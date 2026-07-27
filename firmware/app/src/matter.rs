//! The Matter FanControl endpoint: the fan as Apple Home sees it.
//!
//! rs-matter generates the FanControl cluster (514) shell from the CSA's own normative IDL —
//! attribute IDs, enums, TLV encoding, the `ClusterHandler` trait — but ships no handler for
//! it, because a handler is device logic. This module is that logic, and it is deliberately
//! thin: every decision about what a percentage *means* lives in
//! `stillair_core::matter`, where it is host-tested without a radio, a network, or a board.
//! What is left here is bridging, and bridging is what the compiler can check.
//!
//! **This runs on the thread-mode executor, never on `control`.** The whole reason the
//! executor split exists is that a hung network stack must degrade to the network-loss row of
//! the failure table (the fan keeps its speed) rather than starving the watchdog heartbeat and
//! stopping the fan. Nothing in this file may be spawned onto the interrupt executor.
//!
//! The bridge in both directions is non-blocking by construction: writes `try_send` into the
//! same bounded [`crate::console::COMMANDS`] channel the tuning console uses, and reads come
//! from the telemetry snapshot the control loop republishes every tick. A wedged Matter task
//! therefore cannot block the supervisor, and a wedged supervisor cannot block Matter.

use core::cell::Cell;

use embassy_embedded_hal::adapter::BlockingAsync;
use embassy_sync::blocking_mutex::CriticalSectionMutex;
use embassy_time::{Duration, Timer};
use esp_bootloader_esp_idf::partitions::{
    read_partition_table, DataPartitionSubType, PartitionType, PARTITION_TABLE_MAX_LEN,
};
use esp_hal::peripherals::{ADC1, BT, FLASH, RNG, WIFI};
use esp_hal::rng::{Trng, TrngSource};
use esp_storage::FlashStorage;
use rs_matter_embassy::matter::clusters;
use rs_matter_embassy::matter::crypto::{default_crypto, Crypto};
use rs_matter_embassy::matter::devices;
use rs_matter_embassy::matter::dm::clusters::basic_info::BasicInfoConfig;
use rs_matter_embassy::matter::dm::clusters::decl::fan_control::{
    self, AirflowDirectionEnum, AttributeId, FanModeEnum, FanModeSequenceEnum, StepRequest,
};
use rs_matter_embassy::matter::dm::clusters::desc::{self, ClusterHandler as _};
use rs_matter_embassy::matter::dm::devices::test::{
    DAC_PRIVKEY, TEST_DEV_ATT, TEST_DEV_COMM, TEST_DEV_DET,
};
use rs_matter_embassy::matter::dm::{
    Async, AttrChangeNotifier, Cluster, Dataver, DeviceType, EmptyHandler, Endpoint, EpClMatcher,
    Handler, HandlerContext, InvokeContext, InvokeReply, MatchContext, Node, NonBlockingHandler,
    ReadContext, ReadReply, WriteContext,
};
use rs_matter_embassy::matter::error::{Error, ErrorCode};
use rs_matter_embassy::matter::persist::KvBlobStore;
use rs_matter_embassy::matter::tlv::Nullable;
use rs_matter_embassy::matter::utils::init::InitMaybeUninit;
use rs_matter_embassy::matter::with;
use rs_matter_embassy::persist::SeqMapKvBlobStore;
use rs_matter_embassy::stack::rand::reseeding_csprng;
use rs_matter_embassy::wireless::esp::EspWifiDriver;
use rs_matter_embassy::wireless::{EmbassyWifi, EmbassyWifiMatterStack};
use static_cell::StaticCell;
use stillair_core::config;
use stillair_core::matter as mapping;
use stillair_core::speed::{self, MilliRpm};
use stillair_core::state::{Command, FanState};

use crate::console;

/// Statically allocate a `T` without putting it on the program stack on the way there.
///
/// The Matter stack is tens of kilobytes; constructing it as a temporary and moving it would
/// overflow the stack long before it reached its home.
macro_rules! mk_static {
    ($t:ty) => {{
        static CELL: StaticCell<$t> = StaticCell::new();
        CELL.uninit()
    }};
}

/// Endpoint 0 is the root node's own clusters, so the fan lives on 1.
pub const FAN_ENDPOINT: u16 = 1;

/// Matter device type "Fan" (0x002B).
///
/// Not in `rs_matter::dm::devices`, which stops at the device types it ships handlers for, so
/// it is declared here. Revision 4 is the Matter 1.4 definition.
pub const DEV_TYPE_FAN: DeviceType = DeviceType {
    dtype: 0x002B,
    drev: 4,
};

/// The state Matter owns, as opposed to the state the supervisor owns.
///
/// `PercentSetting` is genuinely the controller's, not the fan's: it is what was *asked for*,
/// and it must read back as written even while the ramp is still minutes away from it —
/// otherwise the slider springs back under the user's finger. `PercentCurrent` is the fan's
/// and comes from the tachometer. Conflating the two is the single most common way a Matter
/// fan misbehaves in a controller UI.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Requested {
    /// 0 means off. Matches the contract's "PercentSetting 0 = Off".
    percent: u8,
    direction: AirflowDirectionEnum,
}

impl Requested {
    const fn new() -> Self {
        Self {
            // Power-on is always off regardless of any persisted attribute
            // (`docs/controls.md` > "Boot never restores a running state"). Matter's
            // StartUpOnOff semantics are deliberately not implemented.
            percent: 0,
            direction: AirflowDirectionEnum::Forward,
        }
    }
}

pub struct FanHandler {
    dataver: Dataver,
    requested: CriticalSectionMutex<Cell<Requested>>,
}

impl FanHandler {
    pub const fn new(dataver: Dataver) -> Self {
        Self {
            dataver,
            requested: CriticalSectionMutex::new(Cell::new(Requested::new())),
        }
    }

    fn requested(&self) -> Requested {
        self.requested.lock(|cell| cell.get())
    }

    /// The bottom of the percent range, which qualification may raise. Taken from the
    /// supervisor rather than assumed, so the mapping Matter uses and the mapping the
    /// supervisor enforces cannot disagree.
    fn released_min(&self) -> MilliRpm {
        console::latest()
            .map(|telemetry| telemetry.released_min)
            .unwrap_or(MilliRpm::from_rpm(config::RPM_USER_MIN_TARGET))
    }

    /// Hand a command to the supervisor. Never blocks: a full queue means the control loop
    /// is not draining it, and stalling the Matter stack on that would convert a control-loop
    /// problem into a network problem for no benefit.
    fn command(&self, command: Command) -> Result<(), Error> {
        console::COMMANDS
            .try_send(command)
            .map_err(|_| Error::from(ErrorCode::Busy))
    }

    /// What the fan is actually doing, as a percentage. Zero whenever it is not running, so a
    /// controller never shows a live speed for a stopped fan.
    fn current_percent(&self) -> u8 {
        let Some(telemetry) = console::latest() else {
            return 0;
        };
        if !matches!(telemetry.state, FanState::Running | FanState::Starting) {
            return 0;
        }
        speed::rpm_to_percent(telemetry.measured_fg, telemetry.released_min)
    }

    /// Re-report to subscribers when the fan's own state has moved.
    ///
    /// Matter subscriptions are driven by the cluster's data version, and only a write bumps
    /// it — so without this a controller would show the speed it last asked for and never the
    /// speed the fan actually reached. The change originates in the control loop rather than
    /// in a Matter write, which is why it needs pushing rather than falling out of a setter.
    fn refresh(&self, notifier: &impl AttrChangeNotifier) {
        self.dataver.changed();
        notifier.notify_cluster_changed(
            FAN_ENDPOINT,
            <Self as fan_control::ClusterHandler>::CLUSTER.id,
        );
    }
}

/// The fan cluster plus the background loop that keeps subscribers current.
///
/// A thin wrapper over the generated adaptor purely so there is somewhere to put `run`, which
/// `rs-matter` drives for every handler in the chain. Read/write/invoke pass straight
/// through — the generated adaptor already decodes and dispatches them.
pub struct FanCluster(fan_control::HandlerAdaptor<&'static FanHandler>);

impl FanCluster {
    pub const fn new(handler: &'static FanHandler) -> Self {
        Self(fan_control::HandlerAdaptor(handler))
    }
}

impl Handler for FanCluster {
    fn read(&self, ctx: impl ReadContext, reply: impl ReadReply) -> Result<(), Error> {
        self.0.read(ctx, reply)
    }

    fn write(&self, ctx: impl WriteContext) -> Result<(), Error> {
        self.0.write(ctx)
    }

    fn invoke(&self, ctx: impl InvokeContext, reply: impl InvokeReply) -> Result<(), Error> {
        self.0.invoke(ctx, reply)
    }

    fn bump_dataver(&self, ctx: impl MatchContext) {
        self.0.bump_dataver(ctx);
    }

    /// Poll the fan's measured speed and re-report it when it moves.
    ///
    /// Deliberately slow: `PercentCurrent` follows a 1.5 RPM/s ramp, so nothing a controller
    /// displays changes faster than this, and every notification costs the network stack work
    /// it would rather spend on the commissioning path.
    async fn run(&self, ctx: impl HandlerContext) -> Result<(), Error> {
        let mut reported = None;
        loop {
            Timer::after(NOTIFY_INTERVAL).await;
            let current = self.0 .0.current_percent();
            if reported != Some(current) {
                reported = Some(current);
                self.0 .0.refresh(&ctx);
            }
        }
    }
}

impl fan_control::ClusterHandler for FanHandler {
    /// Only what this fan actually is: a continuous-speed fan that can reverse.
    ///
    /// `MULTI_SPEED` advertises the discrete `SpeedSetting`/`SpeedMax` attributes, which would
    /// be a second, coarser speed axis fighting the percentage one; `ROCKING` and `WIND` are
    /// oscillation and breeze emulation this fan has no mechanism for; `STEP` is a stepped
    /// remote-control idiom. Advertising a feature we cannot honour is how a controller ends
    /// up sending commands that silently do nothing.
    const CLUSTER: Cluster<'static> = fan_control::FULL_CLUSTER
        .with_features(fan_control::Feature::AIRFLOW_DIRECTION.bits())
        .with_attrs(with!(required; AttributeId::AirflowDirection))
        .with_cmds(with!());

    fn dataver(&self) -> u32 {
        self.dataver.get()
    }

    fn dataver_changed(&self) {
        self.dataver.changed();
    }

    fn fan_mode(&self, _ctx: impl ReadContext) -> Result<FanModeEnum, Error> {
        let requested = self.requested();
        let running = requested.percent > 0;
        Ok(match mapping::mode_for(running, requested.percent) {
            mapping::FanMode::Off => FanModeEnum::Off,
            mapping::FanMode::Low => FanModeEnum::Low,
            mapping::FanMode::Medium => FanModeEnum::Medium,
            mapping::FanMode::High => FanModeEnum::High,
            mapping::FanMode::On | mapping::FanMode::Auto => FanModeEnum::On,
        })
    }

    /// No Auto: this fan has nothing to be automatic about, and offering the mode would
    /// promise a behaviour that does not exist.
    fn fan_mode_sequence(&self, _ctx: impl ReadContext) -> Result<FanModeSequenceEnum, Error> {
        Ok(FanModeSequenceEnum::OffLowMedHigh)
    }

    fn percent_setting(&self, _ctx: impl ReadContext) -> Result<Nullable<u8>, Error> {
        Ok(Nullable::some(self.requested().percent))
    }

    fn percent_current(&self, _ctx: impl ReadContext) -> Result<u8, Error> {
        Ok(self.current_percent())
    }

    fn airflow_direction(&self, _ctx: impl ReadContext) -> Result<AirflowDirectionEnum, Error> {
        Ok(self.requested().direction)
    }

    fn set_fan_mode(&self, _ctx: impl WriteContext, value: FanModeEnum) -> Result<(), Error> {
        let mode = match value {
            FanModeEnum::Off => mapping::FanMode::Off,
            FanModeEnum::Low => mapping::FanMode::Low,
            FanModeEnum::Medium => mapping::FanMode::Medium,
            FanModeEnum::High => mapping::FanMode::High,
            FanModeEnum::On => mapping::FanMode::On,
            // `Smart` is deprecated and defined as a synonym for `Auto`; a controller written
            // against an older spec revision can still send it, and rejecting it would look
            // like a broken accessory rather than a deprecation.
            FanModeEnum::Auto | FanModeEnum::Smart => mapping::FanMode::Auto,
        };
        let released_min = self.released_min();
        self.command(mapping::command_for_mode(mode, released_min))?;

        // Keep `PercentSetting` consistent with the mode just written, or a controller that
        // writes High and then reads the percentage back sees the previous one. `On` and
        // `Auto` carry no percentage — they resume — so the stored setting is what they
        // resume to and must not be overwritten.
        // `On` and `Auto` carry no percentage: they resume whatever speed the supervisor is
        // still holding. Report *that* rather than inventing a number, so the slider a
        // controller draws after an On matches the speed the fan is actually heading for.
        let resumed = console::latest()
            .map(|telemetry| telemetry.target)
            .unwrap_or(released_min);
        self.requested.lock(|cell| {
            let mut requested = cell.get();
            requested.percent = match mode.percent() {
                Some(percent) => percent,
                None => speed::rpm_to_percent(resumed, released_min),
            };
            cell.set(requested);
        });
        self.dataver.changed();
        Ok(())
    }

    fn set_percent_setting(
        &self,
        _ctx: impl WriteContext,
        value: Nullable<u8>,
    ) -> Result<(), Error> {
        // Null means "no explicit setting" rather than zero. Treating it as zero would turn a
        // controller's way of saying nothing into a stop command.
        let Some(percent) = value.into_option() else {
            return Ok(());
        };
        if percent > 100 {
            return Err(ErrorCode::ConstraintError.into());
        }

        let released_min = self.released_min();
        self.command(mapping::command_for_percent(percent, released_min))?;
        self.requested.lock(|cell| {
            let mut requested = cell.get();
            requested.percent = percent;
            cell.set(requested);
        });
        self.dataver.changed();
        Ok(())
    }

    fn set_airflow_direction(
        &self,
        _ctx: impl WriteContext,
        value: AirflowDirectionEnum,
    ) -> Result<(), Error> {
        let direction = match value {
            AirflowDirectionEnum::Forward => mapping::AirflowDirection::Forward,
            AirflowDirectionEnum::Reverse => mapping::AirflowDirection::Reverse,
        };
        // The supervisor decides *when* this takes effect: a reversal ramps to zero, verifies
        // the rotor is stopped, flips DIR, and restarts, which takes far longer than the write
        // acknowledgement. Reporting the requested direction immediately is correct — it is
        // the setting, not the state — and `docs/controls.md` records that the reversal cost
        // is deliberate.
        self.command(mapping::command_for_direction(direction))?;
        self.requested.lock(|cell| {
            let mut requested = cell.get();
            requested.direction = value;
            cell.set(requested);
        });
        self.dataver.changed();
        Ok(())
    }

    /// `STEP` is not among the advertised features, so this is unreachable through a
    /// conformant controller; the trait requires it regardless.
    fn handle_step(
        &self,
        _ctx: impl InvokeContext,
        _request: StepRequest<'_>,
    ) -> Result<(), Error> {
        Err(ErrorCode::CommandNotFound.into())
    }
}

/// Read, write and invoke all complete without awaiting — they touch a `Cell` and a
/// `try_send` — which lets the data model skip buffering the incoming request.
impl NonBlockingHandler for FanCluster {}

/// How Apple Home will name and identify the fan.
///
/// The vendor and product IDs are rs-matter's *test* values, and the attestation credentials
/// below are its test credentials: this is a one-off personal device, not a certified
/// product, so Apple Home shows an "Uncertified Accessory" warning and adds it anyway
/// (`docs/controls.md` > "Home integration"). Certification would be the only way to remove
/// that, and it is not worth it for a fan over one bed.
const DEVICE: BasicInfoConfig<'static> = BasicInfoConfig {
    vendor_name: "Stillair",
    product_name: "Stillair Ceiling Fan",
    device_name: "Ceiling Fan",
    hw_ver: 1,
    hw_ver_str: "V1",
    sw_ver: 1,
    sw_ver_str: env!("CARGO_PKG_VERSION"),
    ..TEST_DEV_DET
};

/// Memory for the futures `rs-matter-stack` creates while running.
///
/// Sized from rs-matter-embassy's own example. If the stack panics during initialisation,
/// this is the number to raise.
const BUMP_SIZE: usize = 20_000;

/// The Matter node: the root endpoint's system clusters, plus our fan.
///
/// No Identify cluster. The Fan device type nominally mandates it, and rs-matter's own
/// examples omit it for On/Off lights too; a ceiling fan has no indicator to flash, so the
/// honest options were an Identify that does nothing or no Identify at all. Revisit if a
/// controller refuses the device over it.
const NODE: Node = Node {
    endpoints: &[
        EmbassyWifiMatterStack::<0, ()>::root_endpoint(),
        Endpoint::new(
            FAN_ENDPOINT,
            devices!(DEV_TYPE_FAN),
            clusters!(
                desc::DescHandler::CLUSTER,
                <FanHandler as fan_control::ClusterHandler>::CLUSTER
            ),
        ),
    ],
};

/// How often the fan's own state is re-reported to Matter subscribers.
///
/// Slow on purpose. `PercentCurrent` follows a 1.5 RPM/s ramp, so nothing a controller
/// displays changes faster than this, and every notification costs the network stack work it
/// would otherwise spend on the commissioning path.
const NOTIFY_INTERVAL: Duration = Duration::from_secs(2);

/// Run the Matter stack. Never returns.
pub async fn run(
    rng: RNG<'static>,
    adc1: ADC1<'static>,
    wifi: WIFI<'static>,
    bt: BT<'static>,
    flash: FLASH<'static>,
) {
    // Statically allocated: the stack is 35-50 KB and would otherwise blow the program stack.
    let stack = mk_static!(EmbassyWifiMatterStack<BUMP_SIZE, ()>).init_with(
        EmbassyWifiMatterStack::init(&DEVICE, TEST_DEV_COMM, &TEST_DEV_ATT),
    );

    // Hardware TRNG seeding a reseeding CSPRNG, rather than anything derived from time —
    // these bytes end up in the commissioning session keys.
    let _trng = TrngSource::new(rng, adc1);
    let crypto = default_crypto(
        reseeding_csprng(Trng::try_new().expect("the TRNG must be available"), 1000)
            .expect("CSPRNG seeding"),
        DAC_PRIVKEY,
    );
    let mut weak_rand = crypto.weak_rand().expect("a weak RNG");

    let fan = mk_static!(FanHandler).write(FanHandler::new(Dataver::new_rand(&mut weak_rand)));
    let descriptor = desc::DescHandler::new(Dataver::new_rand(&mut weak_rand));

    let handler = EmptyHandler
        .chain(
            EpClMatcher::new(
                Some(FAN_ENDPOINT),
                Some(<FanHandler as fan_control::ClusterHandler>::CLUSTER.id),
            ),
            Async(FanCluster::new(fan)),
        )
        .chain(
            EpClMatcher::new(Some(FAN_ENDPOINT), Some(desc::DescHandler::CLUSTER.id)),
            Async(descriptor.adapt()),
        );

    // Flash-backed, not the examples' `DummyKvBlobStore`: without persistence every power
    // cut would demand re-commissioning from Apple Home, and this fan is wired to a ceiling.
    let mut partition_table = [0u8; PARTITION_TABLE_MAX_LEN];
    let mut store = persistent_store(flash, &mut partition_table);
    stack.startup(&crypto, &mut store).await.expect("startup");
    let kv = stack.matter().kv(store);

    log::info!("Matter starting; commission via BLE (QR below)");

    // `run_coex`: Wi-Fi and BLE concurrently, so commissioning does not require dropping the
    // network. The future never completes.
    let result = stack
        .run_coex(
            EmbassyWifi::new(EspWifiDriver::new(wifi, bt), weak_rand, true, stack),
            &crypto,
            (NODE, handler),
            kv,
            (),
        )
        .await;

    // Only reachable if the stack gives up. Say so loudly: the fan keeps running on its last
    // local speed (the network-loss row), but nothing will control it until a reboot.
    log::error!("Matter stack exited: {result:?}");
}

/// The BLOB store, in the first NVS partition of the on-board flash.
///
/// Lifted from rs-matter-embassy's own persistent example rather than invented: where the
/// commissioning state lives has to agree with the partition table `espflash` writes, and
/// guessing at an offset would corrupt something else on the chip.
fn persistent_store<'d>(flash: FLASH<'d>, buf: &mut [u8]) -> impl KvBlobStore + 'd {
    let mut flash = FlashStorage::new(flash);
    let table = read_partition_table(&mut flash, &mut buf[..PARTITION_TABLE_MAX_LEN])
        .expect("a readable partition table");
    let nvs = table
        .find_partition(PartitionType::Data(DataPartitionSubType::Nvs))
        .expect("a searchable partition table")
        .expect("an NVS partition to persist Matter state in");

    let range = nvs.offset()..nvs.offset() + nvs.len();
    log::info!(
        "Matter state persists to NVS {:#x}..{:#x}",
        range.start,
        range.end
    );
    SeqMapKvBlobStore::new(BlockingAsync::new(flash), range)
}
