//! Over-the-air updates through `esp-lan-ota`: the image arrives as Matter commands to a
//! manufacturer cluster on the fan endpoint, over the stack that is already running.
//!
//! The fan-specific decisions (when to stand down, when a reset is safe, what proves a new
//! image healthy) live in `stillair_core::ota`. This module wires them to the board:
//!
//! - New uploads are accepted only while the fan is stopped (or faulted) with no On intent;
//!   otherwise `Begin` answers `Busy` and `esp-ota` retries for two minutes. Once an upload
//!   starts, Matter refuses drive commands and the fan is held off until the reset, which
//!   lands in off anyway. The upload's interrupt-masked flash erases never meet a spinning
//!   motor.
//! - A staged update resets only after the supervisor reports a reset-safe state (bounded).
//! - An unconfirmed image confirms only on whole-product evidence, else it resets after
//!   [`policy::CONFIRM_TIMEOUT_SECS`] and the rollback bootloader returns to the old slot.
//!
//! Everything here runs on the thread-mode executor with Matter, never on `control`.

use alloc::vec;
use core::sync::atomic::{AtomicBool, AtomicU32, Ordering};

use embassy_time::{Duration, Instant, Timer};
use esp_bootloader_esp_idf::partitions::{read_partition_table, PARTITION_TABLE_MAX_LEN};
use esp_hal::peripherals::FLASH;
use esp_lan_ota::matter::{announce_enrollment, Enrollment, OtaCluster, OtaService};
use esp_lan_ota::{Chip, Identity, Name, Ota};
use esp_storage::FlashStorage;
use rs_matter_embassy::matter::dm::{
    Handler, InvokeContext, InvokeReply, MatchContext, NonBlockingHandler, ReadContext, ReadReply,
    WriteContext,
};
use rs_matter_embassy::matter::error::{Error, ErrorCode};
use static_cell::StaticCell;
use stillair_core::ota as policy;

use crate::{console, mcf, wifi_diag};

pub type Service = OtaService<FlashStorage<'static>>;
pub type Cluster = OtaCluster<'static, FlashStorage<'static>>;

/// How often the upload gate and health checks look at the supervisor.
const POLL: Duration = Duration::from_millis(250);

/// An upload is in progress or staged, or a reset is pending: refuse drive commands. Set
/// as soon as an upload starts; cleared only when one ends without staging.
static UPDATE_ACTIVE: AtomicBool = AtomicBool::new(false);

/// Matter requests served on the fan endpoint since boot. Confirmation evidence.
static MATTER_REQUESTS: AtomicU32 = AtomicU32::new(0);

pub fn update_active() -> bool {
    UPDATE_ACTIVE.load(Ordering::Acquire)
}

/// Counts a successfully served Matter request.
pub fn served<T>(result: Result<T, Error>) -> Result<T, Error> {
    if result.is_ok() {
        MATTER_REQUESTS.fetch_add(1, Ordering::Relaxed);
    }
    result
}

/// Reads the boot records and returns the shared OTA state, or `None` (logged) when the
/// flash does not carry the OTA partition table. Matter then runs without updates.
pub fn start(flash: FLASH<'static>) -> Option<&'static Service> {
    static SERVICE: StaticCell<Service> = StaticCell::new();

    let mut flash = FlashStorage::new(flash);
    // Which slot is running, from the MMU mapping. The 3 KiB table copy is needed only here,
    // so it is a short-lived heap buffer rather than permanent static or stack space.
    let booted = {
        let mut buf = vec![0u8; PARTITION_TABLE_MAX_LEN];
        read_partition_table(&mut flash, &mut buf)
            .ok()
            .and_then(|table| table.booted_partition().ok().flatten())
            .map(|partition| partition.offset())
    };
    let Some(booted) = booted else {
        log::error!("OTA disabled: booted partition not found in the partition table");
        return None;
    };
    let desc = &crate::ESP_APP_DESC;
    let (Some(project), Some(version)) =
        (Name::new(desc.project_name()), Name::new(desc.version()))
    else {
        log::error!("OTA disabled: app descriptor names exceed 32 bytes");
        return None;
    };
    let identity = Identity {
        chip: Chip::Esp32c6,
        project,
        version,
    };
    let ota = match Ota::start(flash, booted, identity) {
        Ok(ota) => ota,
        Err(error) => {
            log::error!("OTA disabled ({error:?}): flash the OTA partition table over USB");
            return None;
        }
    };
    let boot = ota.boot_info();
    log::info!(
        "OTA: {} {} in {:?}, image state {:?}, rollback {}",
        desc.project_name(),
        desc.version(),
        boot.booted,
        boot.state,
        boot.rollback.name()
    );
    Some(SERVICE.init(OtaService::new(ota)))
}

/// The OTA cluster handler, counting served requests. Without OTA state every request is
/// refused, so the node layout stays fixed either way.
pub struct OtaHandler(pub Option<Cluster>);

impl Handler for OtaHandler {
    fn read(&self, ctx: impl ReadContext, reply: impl ReadReply) -> Result<(), Error> {
        match &self.0 {
            Some(cluster) => served(cluster.read(ctx, reply)),
            None => Err(ErrorCode::ClusterNotFound.into()),
        }
    }

    fn write(&self, ctx: impl WriteContext) -> Result<(), Error> {
        match &self.0 {
            Some(cluster) => cluster.write(ctx),
            None => Err(ErrorCode::ClusterNotFound.into()),
        }
    }

    fn invoke(&self, ctx: impl InvokeContext, reply: impl InvokeReply) -> Result<(), Error> {
        match &self.0 {
            Some(cluster) => served(cluster.invoke(ctx, reply)),
            None => Err(ErrorCode::ClusterNotFound.into()),
        }
    }

    fn bump_dataver(&self, ctx: impl MatchContext) {
        if let Some(cluster) = &self.0 {
            cluster.bump_dataver(ctx);
        }
    }
}

impl NonBlockingHandler for OtaHandler {}

/// Prints the line `esp-ota enroll` reads from the USB console while the post-USB-flash
/// commissioning window is open.
#[embassy_executor::task]
pub async fn announce_task(ota: &'static Service, enrollment: Enrollment) {
    // Ends the enrollment period after the window's 15 minutes; the first upload also ends it.
    announce_enrollment(ota, enrollment, |line| log::info!("{line}")).await;
}

/// Opens the upload gate only while the fan is stopped (or faulted) with no On intent.
#[embassy_executor::task]
pub async fn gate_task(ota: &'static Service) {
    let mut accepting = None;
    loop {
        let ready = console::latest()
            .is_some_and(|telemetry| policy::accepts_upload(telemetry.state, telemetry.on));
        if accepting != Some(ready) {
            ota.set_accepting(ready);
            accepting = Some(ready);
        }
        Timer::after(POLL).await;
    }
}

/// Holds the fan off from the start of each upload until it is staged (then the reboot task
/// takes over) or dropped.
#[embassy_executor::task]
pub async fn upload_task(ota: &'static Service) {
    loop {
        ota.wait_upload_started().await;
        UPDATE_ACTIVE.store(true, Ordering::Release);
        log::warn!("OTA upload started: holding the fan off and refusing drive commands");
        while ota.is_updating() {
            stand_down();
            Timer::after(POLL).await;
        }
        UPDATE_ACTIVE.store(false, Ordering::Release);
        log::info!("OTA upload ended without staging; drive commands accepted again");
    }
}

/// Reboots into a staged update once the fan is in a reset-safe state.
#[embassy_executor::task]
pub async fn reboot_task(ota: &'static Service) {
    ota.wait_reboot().await;
    log::warn!("OTA update staged; rebooting into it once the fan is stopped");
    reset_when_safe().await
}

/// Confirms an updated image on whole-product evidence, or resets to roll it back.
#[embassy_executor::task]
pub async fn confirm_task(ota: &'static Service) {
    if !ota.is_unconfirmed() {
        return;
    }
    log::warn!(
        "running an unconfirmed OTA image: confirming once healthy, rolling back after {} s",
        policy::CONFIRM_TIMEOUT_SECS
    );
    let deadline = Instant::now() + Duration::from_secs(policy::CONFIRM_TIMEOUT_SECS);
    let mut reported = None;
    loop {
        match policy::check(&evidence()) {
            Ok(()) => match ota.confirm() {
                Ok(_) => {
                    log::info!("OTA image confirmed");
                    return;
                }
                Err(error) => log::error!("OTA confirm write failed: {error:?}"),
            },
            Err(missing) if reported != Some(missing) => {
                log::info!("OTA image not yet confirmed: {}", missing.as_str());
                reported = Some(missing);
            }
            Err(_) => {}
        }
        if Instant::now() >= deadline {
            log::error!(
                "OTA image unhealthy after {} s ({}); resetting to roll back",
                policy::CONFIRM_TIMEOUT_SECS,
                reported.map_or("confirm write failed", policy::Missing::as_str)
            );
            reset_when_safe().await;
        }
        Timer::after(POLL * 4).await;
    }
}

fn evidence() -> policy::Evidence {
    let telemetry = console::latest();
    policy::Evidence {
        control_beats: crate::CONTROL_LOOP_BEAT.load(Ordering::Relaxed),
        mcf_status_reads: mcf::STATUS_READS_OK.load(Ordering::Relaxed),
        mcf_status_failing: mcf::STATUS_FAILING.load(Ordering::Relaxed),
        state: telemetry.map(|telemetry| telemetry.state),
        config: telemetry
            .map(|telemetry| telemetry.config)
            .unwrap_or_default(),
        wifi_connected: wifi_diag::snapshot().connected,
        matter_requests: MATTER_REQUESTS.load(Ordering::Relaxed),
    }
}

/// Moves the fan one step toward a reset-safe state. Returns whether it is there.
fn stand_down() -> bool {
    let Some(telemetry) = console::latest() else {
        return false;
    };
    match policy::quiesce_command(telemetry.state, telemetry.on) {
        Some(command) => {
            // A full queue means the control loop has not drained it yet; the next poll
            // sends again.
            let _ = console::COMMANDS.try_send(command);
            false
        }
        None => policy::reset_safe(telemetry.state),
    }
}

/// Stops the fan, waits (bounded) for a reset-safe state, then resets.
async fn reset_when_safe() -> ! {
    UPDATE_ACTIVE.store(true, Ordering::Release);
    let deadline = Instant::now() + Duration::from_secs(policy::QUIESCE_TIMEOUT_SECS);
    while !stand_down() {
        if Instant::now() >= deadline {
            log::warn!(
                "fan not reset-safe after {} s; resetting anyway (boot revokes drive)",
                policy::QUIESCE_TIMEOUT_SECS
            );
            break;
        }
        Timer::after(POLL).await;
    }
    log::warn!("resetting");
    // Let the console writer drain the last lines.
    Timer::after(Duration::from_millis(200)).await;
    esp_hal::system::software_reset()
}
