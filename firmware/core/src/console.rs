//! The tuning console: a line protocol for driving and observing the fan from a host.
//!
//! This exists so motor tuning is a scripted, machine-readable activity rather than a
//! person watching a serial log. Requests are plain text, so they can be typed by hand;
//! replies are single-line JSON prefixed with [`PREFIX`], so a tool can parse them without
//! ambiguity. Human log output never begins with that prefix, which is what lets the two
//! share one serial link.
//!
//! Parsing and formatting live here, in the host-testable crate, precisely because a
//! harness that silently mis-parses a command is worse than no harness: it would report
//! confident numbers about a test that never ran.

use core::fmt::Write;

use heapless::String;

use crate::mcf8316::{reg, McfCondition};
use crate::speed::{MilliRpm, SpeedDuty};
use crate::state::{Direction, FanState, FaultReason};

/// Every protocol line begins with this. Log lines never do.
pub const PREFIX: char = '@';

/// Enough for the longest telemetry frame with room to spare.
pub const LINE_CAPACITY: usize = 320;

/// A formatted protocol line, ready to write to the link in one call.
pub type Line = String<LINE_CAPACITY>;

/// A parsed console request.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Request {
    /// One-shot telemetry snapshot.
    State,
    /// Command a speed in whole RPM. Clamped by the supervisor exactly like a Matter
    /// command, so this is a convenience rather than a way around the speed limits.
    /// (`RegWrite` is not so constrained — see its note.)
    Run(MilliRpm),
    Stop,
    SetDirection(Direction),
    RegRead(u16),
    /// Raw register access, deliberately outside every supervisor safeguard: it is how
    /// configuration gets *derived* at the bench, so it cannot be limited to values the
    /// firmware already knows. The device gates writes to the persistent configuration
    /// block on the motor being stopped; nothing else is checked.
    RegWrite {
        address: u16,
        value: u32,
    },
    /// `Some(hz)` starts streaming telemetry at that rate; `None` stops it.
    Stream(Option<u32>),
    /// Issue CLR_FLT. Counts as a fresh user command, exactly like a Matter command.
    ClearFault,
    /// List the commands.
    Help,
}

/// Why a request could not be understood. Reported back rather than ignored, so a script
/// that sends nonsense finds out immediately instead of waiting for a state change that
/// will never come.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParseError {
    Empty,
    UnknownCommand,
    /// A required argument was absent.
    MissingArgument,
    /// An argument was present but unparseable, or out of range.
    BadArgument,
    /// A register name that is not in the map, and not a raw address.
    UnknownRegister,
}

impl ParseError {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Empty => "empty",
            Self::UnknownCommand => "unknown command",
            Self::MissingArgument => "missing argument",
            Self::BadArgument => "bad argument",
            Self::UnknownRegister => "unknown register",
        }
    }
}

/// Parse one request line.
///
/// Accepts numbers in decimal or `0x` hex, and registers by name or raw address. Names are
/// case-insensitive; commands are not case-sensitive either, because a tuning session is
/// typed by hand as often as it is scripted.
pub fn parse(line: &str) -> Result<Request, ParseError> {
    let mut words = line.split_whitespace();
    let command = words.next().ok_or(ParseError::Empty)?;
    let mut argument = || words.next().ok_or(ParseError::MissingArgument);

    // `eq_ignore_ascii_case` rather than lowercasing: this crate has no allocator, and
    // `str::to_ascii_lowercase` would need one.
    let is = |word: &str, expected: &str| word.eq_ignore_ascii_case(expected);

    if is(command, "state") {
        Ok(Request::State)
    } else if is(command, "stop") {
        Ok(Request::Stop)
    } else if is(command, "help") {
        Ok(Request::Help)
    } else if is(command, "run") {
        let rpm: u32 = parse_number(argument()?)?;
        Ok(Request::Run(MilliRpm::from_rpm(rpm)))
    } else if is(command, "dir") {
        let which = argument()?;
        if is(which, "fwd") || is(which, "forward") {
            Ok(Request::SetDirection(Direction::Forward))
        } else if is(which, "rev") || is(which, "reverse") {
            Ok(Request::SetDirection(Direction::Reverse))
        } else {
            Err(ParseError::BadArgument)
        }
    } else if is(command, "fault") {
        if is(argument()?, "clear") {
            Ok(Request::ClearFault)
        } else {
            Err(ParseError::BadArgument)
        }
    } else if is(command, "stream") {
        let mode = argument()?;
        if is(mode, "off") {
            Ok(Request::Stream(None))
        } else if is(mode, "on") {
            let hz: u32 = parse_number(argument()?)?;
            if hz == 0 || hz > MAX_STREAM_HZ {
                return Err(ParseError::BadArgument);
            }
            Ok(Request::Stream(Some(hz)))
        } else {
            Err(ParseError::BadArgument)
        }
    } else if is(command, "reg") {
        let operation = argument()?;
        let address = parse_register(argument()?)?;
        if is(operation, "read") {
            Ok(Request::RegRead(address))
        } else if is(operation, "write") {
            let value = parse_number(argument()?)?;
            Ok(Request::RegWrite { address, value })
        } else {
            Err(ParseError::BadArgument)
        }
    } else {
        Err(ParseError::UnknownCommand)
    }
}

/// Upper bound on the telemetry stream rate. Above this the link becomes the bottleneck and
/// frames would be dropped, which is worse than sampling more slowly on purpose.
pub const MAX_STREAM_HZ: u32 = 100;

fn parse_number<T: TryFrom<u64>>(text: &str) -> Result<T, ParseError> {
    let value = match text.strip_prefix("0x").or_else(|| text.strip_prefix("0X")) {
        Some(hex) => u64::from_str_radix(hex, 16),
        None => text.parse::<u64>(),
    }
    .map_err(|_| ParseError::BadArgument)?;
    T::try_from(value).map_err(|_| ParseError::BadArgument)
}

fn parse_register(text: &str) -> Result<u16, ParseError> {
    if let Some(address) = reg::by_name(text) {
        return Ok(address);
    }
    // A raw address is allowed so a register the map does not name yet is still reachable —
    // the whole point of the console is to work things out that source does not know.
    let address: u16 = parse_number(text).map_err(|_| ParseError::UnknownRegister)?;
    if address > 0x0FFF {
        return Err(ParseError::UnknownRegister);
    }
    Ok(address)
}

/// A telemetry snapshot: everything worth logging about one instant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Telemetry {
    pub uptime_ms: u64,
    pub state: FanState,
    pub fault: Option<FaultReason>,
    /// What the supervisor is commanding, after ramping and clamping.
    pub commanded: MilliRpm,
    /// Measured from FG, at 20 pulses/rev.
    pub measured_fg: MilliRpm,
    /// Measured from the rotor Hall, at 1 pulse/rev. Reported separately rather than
    /// averaged in: the two disagreeing is a diagnosis, not noise to smooth away.
    pub measured_hall: MilliRpm,
    pub duty: SpeedDuty,
    pub direction: Direction,
    /// Protocol lines discarded because the host was not reading fast enough.
    ///
    /// Carried in the frame rather than logged, so a capture with a gap in it is
    /// identifiable *from the capture*. A CSV that is quietly short looks exactly like a
    /// complete one, and a harness that cannot tell you it lost data is a harness that
    /// lies by omission.
    pub dropped: u32,
}

impl Telemetry {
    /// Render as one protocol line.
    pub fn to_line(&self) -> Line {
        let mut line = Line::new();
        // Capacity is checked by test; a truncated frame is dropped by the parser rather
        // than misread, so a write failure here is not silently corrupting anything.
        let _ = write!(
            line,
            "{PREFIX}{{\"type\":\"telemetry\",\"t\":{},\"state\":\"{}\",\"fault\":{},\
             \"cmd_mrpm\":{},\"fg_mrpm\":{},\"hall_mrpm\":{},\"duty\":{},\"dir\":\"{}\",\
             \"dropped\":{}}}",
            self.uptime_ms,
            state_name(self.state),
            OptionalFault(self.fault),
            self.commanded.0,
            self.measured_fg.0,
            self.measured_hall.0,
            self.duty.0,
            direction_name(self.direction),
            self.dropped,
        );
        line
    }
}

/// A reply to a request.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reply<'a> {
    /// The command was accepted. Acceptance is not completion: `run` returns as soon as the
    /// target is set, long before the ramp reaches it.
    Ok,
    /// A register's value.
    Register {
        address: u16,
        value: u32,
    },
    Telemetry(Telemetry),
    Error(&'a str),
}

impl Reply<'_> {
    pub fn to_line(&self) -> Line {
        let mut line = Line::new();
        let _ = match self {
            Self::Ok => write!(line, "{PREFIX}{{\"ok\":true}}"),
            Self::Register { address, value } => {
                let name = reg::name_of(*address).unwrap_or("");
                write!(
                    line,
                    "{PREFIX}{{\"ok\":true,\"addr\":{address},\"name\":\"{name}\",\"value\":{value}}}"
                )
            }
            Self::Telemetry(telemetry) => return telemetry.to_line(),
            Self::Error(message) => {
                write!(line, "{PREFIX}{{\"ok\":false,\"error\":\"{message}\"}}")
            }
        };
        line
    }
}

/// One line per command, for `help`. Plain text, not JSON: this one is for a human.
pub const HELP: &[&str] = &[
    "state                     one telemetry snapshot",
    "run <rpm>                 command a speed (clamped to the released range)",
    "stop                      command off",
    "dir fwd|rev               set direction (takes effect from a verified stop)",
    "reg read <name|addr>      read a 32-bit register",
    "reg write <name|addr> <v> write a 32-bit register",
    "stream on <hz>|off        continuous telemetry, 1-100 Hz (deduped to the control rate)",
    "fault clear               issue CLR_FLT (counts as a fresh user command)",
];

pub const fn state_name(state: FanState) -> &'static str {
    match state {
        FanState::SafeBoot => "safe_boot",
        FanState::IdleOff => "idle_off",
        FanState::Starting => "starting",
        FanState::Running => "running",
        FanState::Stopping => "stopping",
        FanState::Reversing => "reversing",
        FanState::Fault => "fault",
    }
}

pub const fn direction_name(direction: Direction) -> &'static str {
    match direction {
        Direction::Forward => "fwd",
        Direction::Reverse => "rev",
    }
}

pub const fn fault_name(fault: FaultReason) -> &'static str {
    match fault {
        FaultReason::McfFault => "mcf_fault",
        FaultReason::McfAlarm => "mcf_alarm",
        FaultReason::Mcf(condition) => condition_name(condition),
        FaultReason::BusUnreachable => "bus_unreachable",
        FaultReason::RailLoss => "rail_loss",
        FaultReason::HallImplausible => "hall_implausible",
        FaultReason::NoRotation => "no_rotation",
        FaultReason::NeverStopped => "never_stopped",
    }
}

pub const fn condition_name(condition: McfCondition) -> &'static str {
    match condition {
        McfCondition::Undervoltage => "undervoltage",
        McfCondition::Overvoltage => "overvoltage",
        McfCondition::Overtemperature => "overtemperature",
        McfCondition::Overcurrent => "overcurrent",
        McfCondition::MotorLock => "motor_lock",
        McfCondition::StartFailed => "start_failed",
        McfCondition::McfWatchdog => "mcf_watchdog",
        McfCondition::Eeprom => "eeprom",
        McfCondition::ProtocolError => "protocol_error",
        McfCondition::Unclassified => "unclassified",
    }
}

/// Renders `null` or a quoted name, so the field is always present and always valid JSON.
struct OptionalFault(Option<FaultReason>);

impl core::fmt::Display for OptionalFault {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self.0 {
            None => formatter.write_str("null"),
            Some(fault) => write!(formatter, "\"{}\"", fault_name(fault)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_commands_parse() {
        assert_eq!(parse("state"), Ok(Request::State));
        assert_eq!(parse("stop"), Ok(Request::Stop));
        assert_eq!(parse("help"), Ok(Request::Help));
        assert_eq!(parse("fault clear"), Ok(Request::ClearFault));
    }

    #[test]
    fn commands_and_arguments_are_case_insensitive() {
        assert_eq!(parse("STATE"), Ok(Request::State));
        assert_eq!(
            parse("DIR Rev"),
            Ok(Request::SetDirection(Direction::Reverse))
        );
        assert_eq!(parse("reg READ vm_voltage"), Ok(Request::RegRead(0x47C)));
    }

    #[test]
    fn whitespace_and_blank_lines_are_handled() {
        assert_eq!(parse("   state   "), Ok(Request::State));
        assert_eq!(parse(""), Err(ParseError::Empty));
        assert_eq!(parse("   "), Err(ParseError::Empty));
        assert_eq!(
            parse("\t run \t 60 \t"),
            Ok(Request::Run(MilliRpm::from_rpm(60)))
        );
    }

    #[test]
    fn run_takes_whole_rpm() {
        assert_eq!(parse("run 60"), Ok(Request::Run(MilliRpm::from_rpm(60))));
        assert_eq!(parse("run 0"), Ok(Request::Run(MilliRpm::ZERO)));
        assert_eq!(parse("run"), Err(ParseError::MissingArgument));
        assert_eq!(parse("run fast"), Err(ParseError::BadArgument));
        assert_eq!(parse("run -5"), Err(ParseError::BadArgument));
    }

    #[test]
    fn directions_accept_both_spellings_but_nothing_else() {
        for text in ["dir fwd", "dir forward"] {
            assert_eq!(parse(text), Ok(Request::SetDirection(Direction::Forward)));
        }
        for text in ["dir rev", "dir reverse"] {
            assert_eq!(parse(text), Ok(Request::SetDirection(Direction::Reverse)));
        }
        assert_eq!(parse("dir sideways"), Err(ParseError::BadArgument));
        assert_eq!(parse("dir"), Err(ParseError::MissingArgument));
    }

    #[test]
    fn registers_resolve_by_name_or_raw_address() {
        assert_eq!(parse("reg read ISD_CONFIG"), Ok(Request::RegRead(0x080)));
        assert_eq!(parse("reg read 0x080"), Ok(Request::RegRead(0x080)));
        assert_eq!(parse("reg read 128"), Ok(Request::RegRead(0x080)));
        assert_eq!(
            parse("reg write ALGO_CTRL1 0x30000000"),
            Ok(Request::RegWrite {
                address: 0x0EA,
                value: 0x3000_0000
            })
        );
    }

    #[test]
    fn an_address_outside_the_field_is_refused() {
        // MEM_ADDR is 12 bits; anything larger would silently alias.
        assert_eq!(parse("reg read 0x1000"), Err(ParseError::UnknownRegister));
        assert_eq!(
            parse("reg read NOT_A_REGISTER"),
            Err(ParseError::UnknownRegister)
        );
    }

    #[test]
    fn a_register_write_needs_its_value() {
        assert_eq!(
            parse("reg write ISD_CONFIG"),
            Err(ParseError::MissingArgument)
        );
        assert_eq!(
            parse("reg write ISD_CONFIG xyz"),
            Err(ParseError::BadArgument)
        );
        assert_eq!(parse("reg poke ISD_CONFIG 1"), Err(ParseError::BadArgument));
    }

    #[test]
    fn a_full_width_register_value_survives_parsing() {
        // u32::MAX must not be rejected as out of range by the u64 intermediate.
        assert_eq!(
            parse("reg write 0x080 0xFFFFFFFF"),
            Ok(Request::RegWrite {
                address: 0x080,
                value: u32::MAX
            })
        );
        assert_eq!(
            parse("reg write 0x080 0x100000000"),
            Err(ParseError::BadArgument),
            "a value wider than the register was accepted"
        );
    }

    #[test]
    fn stream_rates_are_bounded() {
        assert_eq!(parse("stream on 10"), Ok(Request::Stream(Some(10))));
        assert_eq!(parse("stream off"), Ok(Request::Stream(None)));
        assert_eq!(parse("stream on 0"), Err(ParseError::BadArgument));
        assert_eq!(parse("stream on 1000"), Err(ParseError::BadArgument));
        assert_eq!(parse("stream on"), Err(ParseError::MissingArgument));
    }

    #[test]
    fn unknown_commands_are_reported_not_ignored() {
        assert_eq!(parse("frobnicate"), Err(ParseError::UnknownCommand));
    }

    fn sample() -> Telemetry {
        Telemetry {
            uptime_ms: 12_345,
            state: FanState::Running,
            fault: None,
            commanded: MilliRpm::from_rpm(60),
            measured_fg: MilliRpm(59_800),
            measured_hall: MilliRpm(60_100),
            duty: SpeedDuty(683),
            direction: Direction::Forward,
            dropped: 0,
        }
    }

    #[test]
    fn a_telemetry_line_is_prefixed_and_complete() {
        let line = sample().to_line();
        assert!(line.starts_with(PREFIX));
        assert!(line.ends_with('}'), "line was truncated: {line}");
        for field in [
            "\"t\":12345",
            "\"state\":\"running\"",
            "\"fault\":null",
            "\"cmd_mrpm\":60000",
            "\"fg_mrpm\":59800",
            "\"hall_mrpm\":60100",
            "\"duty\":683",
            "\"dir\":\"fwd\"",
            "\"dropped\":0",
        ] {
            assert!(line.contains(field), "missing {field} in {line}");
        }
    }

    #[test]
    fn a_fault_is_named_rather_than_dropped() {
        let mut telemetry = sample();
        telemetry.state = FanState::Fault;
        telemetry.fault = Some(FaultReason::Mcf(McfCondition::Undervoltage));
        let line = telemetry.to_line();
        assert!(line.contains("\"fault\":\"undervoltage\""), "{line}");
    }

    #[test]
    fn the_widest_telemetry_line_still_fits() {
        // Every field at its maximum width, so a real frame can never be truncated.
        let telemetry = Telemetry {
            uptime_ms: u64::MAX,
            state: FanState::Reversing,
            fault: Some(FaultReason::HallImplausible),
            commanded: MilliRpm(u32::MAX),
            measured_fg: MilliRpm(u32::MAX),
            measured_hall: MilliRpm(u32::MAX),
            duty: SpeedDuty(u16::MAX),
            direction: Direction::Reverse,
            dropped: u32::MAX,
        };
        let line = telemetry.to_line();
        assert!(line.ends_with('}'), "truncated at {} bytes", line.len());
        assert!(line.len() < LINE_CAPACITY);
    }

    #[test]
    fn replies_are_prefixed_json() {
        assert_eq!(Reply::Ok.to_line().as_str(), "@{\"ok\":true}");
        assert_eq!(
            Reply::Error("unknown command").to_line().as_str(),
            "@{\"ok\":false,\"error\":\"unknown command\"}"
        );
    }

    #[test]
    fn a_register_reply_labels_the_address_when_it_can() {
        let line = Reply::Register {
            address: 0x47C,
            value: 24_000,
        }
        .to_line();
        assert!(line.contains("\"name\":\"VM_VOLTAGE\""), "{line}");
        assert!(line.contains("\"value\":24000"), "{line}");

        // An address the map does not name still round-trips, with an empty name.
        let line = Reply::Register {
            address: 0x123,
            value: 7,
        }
        .to_line();
        assert!(line.contains("\"name\":\"\""), "{line}");
        assert!(line.contains("\"addr\":291"), "{line}");
    }

    #[test]
    fn every_named_register_is_reachable_by_name_and_unique() {
        let mut seen = std::collections::HashSet::new();
        for (name, address) in reg::NAMED {
            assert_eq!(reg::by_name(name), Some(*address), "{name}");
            assert!(*address <= 0x0FFF, "{name} overflows MEM_ADDR");
            assert!(seen.insert(*name), "duplicate register name {name}");
        }
    }

    #[test]
    fn every_fault_and_state_has_a_distinct_name() {
        // A name collision would make two different conditions indistinguishable in a log
        // that is meant to be the record of what happened on the bench.
        let states = [
            FanState::SafeBoot,
            FanState::IdleOff,
            FanState::Starting,
            FanState::Running,
            FanState::Stopping,
            FanState::Reversing,
            FanState::Fault,
        ];
        let names: std::collections::HashSet<_> = states.iter().map(|s| state_name(*s)).collect();
        assert_eq!(names.len(), states.len());

        let faults = [
            FaultReason::McfFault,
            FaultReason::McfAlarm,
            FaultReason::BusUnreachable,
            FaultReason::RailLoss,
            FaultReason::HallImplausible,
            FaultReason::NoRotation,
            FaultReason::NeverStopped,
            FaultReason::Mcf(McfCondition::Undervoltage),
            FaultReason::Mcf(McfCondition::Overvoltage),
            FaultReason::Mcf(McfCondition::Overtemperature),
            FaultReason::Mcf(McfCondition::Overcurrent),
            FaultReason::Mcf(McfCondition::MotorLock),
            FaultReason::Mcf(McfCondition::StartFailed),
            FaultReason::Mcf(McfCondition::McfWatchdog),
            FaultReason::Mcf(McfCondition::Eeprom),
            FaultReason::Mcf(McfCondition::ProtocolError),
            FaultReason::Mcf(McfCondition::Unclassified),
        ];
        let names: std::collections::HashSet<_> = faults.iter().map(|f| fault_name(*f)).collect();
        assert_eq!(names.len(), faults.len());
    }
}
