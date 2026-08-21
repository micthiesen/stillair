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

use embassy_embedded_hal::adapter::BlockingAsync;
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
use stillair_core::speed::MilliRpm;
use stillair_core::state::Command;

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

/// The FanControl attributes, derived from the supervisor rather than cached.
///
/// **There is deliberately no local copy of the requested state.** An earlier version kept
/// one, on the reasoning that `PercentSetting` is the controller's state rather than the
/// fan's. That is true, but the controller is not the only source of it: the serial tuning
/// console writes the same commands into the same channel, and the supervisor itself clears
/// the request on a fault or a stop. A Matter-private cache has no path back from any of
/// those, so it would sit there reporting "High" at a fan that faulted an hour ago, and no
/// amount of re-reporting would fix it — the re-report would serve the same stale value.
///
/// So the supervisor owns the intent (`target`, `commanded_on`, `requested_direction`) and
/// this reads it. Divergence stops being something to keep in sync and becomes unrepresentable.
/// The FanControl attributes, derived from the supervisor rather than cached.
///
/// **There is deliberately no local copy of the requested state.** An earlier version kept
/// one, on the reasoning that `PercentSetting` is the controller's state rather than the
/// fan's. That is true, but the controller is not the only source of it: the serial tuning
/// console writes the same commands into the same channel, and the supervisor itself clears
/// the request on a fault or a stop. A Matter-private cache has no path back from any of
/// those, so it would sit there reporting "High" at a fan that faulted an hour ago, and no
/// amount of re-reporting would fix it — the re-report would serve the same stale value.
///
/// So the supervisor owns the intent (`target`, `commanded_on`, `requested_direction`) and
/// this reads it. Divergence stops being something to keep in sync and becomes unrepresentable.
pub struct FanHandler {
    dataver: Dataver,
}

impl FanHandler {
    pub const fn new(dataver: Dataver) -> Self {
        Self { dataver }
    }

    /// Everything reported to Matter, in one consistent snapshot.
    ///
    /// The derivation lives in `stillair-core` so it is host-tested; this is the read of the
    /// telemetry the control loop republishes every tick.
    fn reported(&self) -> mapping::Reported {
        console::latest()
            .map(|telemetry| mapping::reported(&telemetry))
            .unwrap_or_default()
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
        if command.starts_drive()
            && !console::latest()
                .map(|telemetry| telemetry.config.permits_operation())
                .unwrap_or(false)
        {
            return Err(Error::from(ErrorCode::Busy));
        }
        console::COMMANDS
            .try_send(command)
            .map_err(|_| Error::from(ErrorCode::Busy))
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
    /// Deliberately slow: `PercentCurrent` follows the physical rotor, so nothing a controller
    /// displays changes faster than this, and every notification costs the network stack work
    /// it would rather spend on the commissioning path.
    async fn run(&self, ctx: impl HandlerContext) -> Result<(), Error> {
        let mut last = None;
        loop {
            Timer::after(NOTIFY_INTERVAL).await;
            // The whole reported snapshot, not just the measured speed: the serial console
            // writes the same commands into the same channel, and a fault clears the request
            // outright. Watching only what Matter itself wrote would leave a controller
            // showing a setting nobody holds any more.
            let current = self.0 .0.reported();
            if last != Some(current) {
                last = Some(current);
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
        Ok(match mapping::reported_mode(self.reported()) {
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
        Ok(Nullable::some(self.reported().setting))
    }

    fn percent_current(&self, _ctx: impl ReadContext) -> Result<u8, Error> {
        Ok(self.reported().current)
    }

    fn airflow_direction(&self, _ctx: impl ReadContext) -> Result<AirflowDirectionEnum, Error> {
        Ok(match self.reported().direction {
            mapping::AirflowDirection::Forward => AirflowDirectionEnum::Forward,
            mapping::AirflowDirection::Reverse => AirflowDirectionEnum::Reverse,
        })
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

        // Nothing to store: `PercentSetting` and `FanMode` are both read back from the
        // supervisor, so the command above *is* the state change. `On` and `Auto` carry no
        // percentage and resume the supervisor's standing target, which the read path already
        // reports.
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
/// Slow on purpose. `PercentCurrent` follows the physical rotor, so nothing a controller
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
    //
    // TODO(temp-sense): taking ADC1 whole here is why TEMP_SENSE (GPIO6/ADC1_CH6, the
    // motor NTC divider on PCB-01) is wired but unread — the behavioral contract's
    // overtemperature stop currently has no input. Implementing it means sharing ADC1
    // between TrngSource's entropy sampling and a periodic GPIO6 conversion (esp-hal's
    // TrngSource holds the peripheral; check whether a later esp-hal exposes shared/split
    // ADC access, else sample temperature before constructing the TRNG or drop to raw
    // register access). Tracked in docs/electrical.md > "Open items from the 2026-07
    // board-truth review".
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
    let Some(mut store) = persistent_store(flash, &mut partition_table) else {
        log::error!("no NVS partition; Matter will not start, the fan keeps local control");
        return;
    };
    if let Err(error) = stack.startup(&crypto, &mut store).await {
        // Deliberately not a panic. A panic takes the whole binary down, control loop
        // included, and stops a fan that was running perfectly well — the opposite of the
        // network-loss row of the failure table. Losing Matter must lose only Matter.
        log::error!("Matter startup failed ({error:?}); the fan keeps local control");
        return;
    }
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
fn persistent_store<'d>(flash: FLASH<'d>, buf: &mut [u8]) -> Option<impl KvBlobStore + 'd> {
    let mut flash = FlashStorage::new(flash);
    let table = read_partition_table(&mut flash, &mut buf[..PARTITION_TABLE_MAX_LEN]).ok()?;
    let nvs = table
        .find_partition(PartitionType::Data(DataPartitionSubType::Nvs))
        .ok()??;

    let range = nvs.offset()..nvs.offset() + nvs.len();
    log::info!(
        "Matter state persists to NVS {:#x}..{:#x}",
        range.start,
        range.end
    );
    Some(SeqMapKvBlobStore::new(BlockingAsync::new(flash), range))
}
