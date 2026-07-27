//! `stillair` — the host end of the tuning harness.
//!
//! Drives a supervisor over the console protocol, against either a real board (`--port`) or
//! the simulator (`--sim`). Everything it prints is machine-readable and it exits non-zero
//! on failure, so a tuning or commissioning step is a shell command with an exit code rather
//! than a person reading a serial log.
//!
//! ```text
//! stillair --sim state
//! stillair --port /dev/tty.usbmodem1101 run 60
//! stillair --port /dev/tty.usbmodem1101 wait running --for 30
//! stillair --sim stream 10 --for 120 > sweep.csv
//! stillair --sim reg read VM_VOLTAGE
//! ```

use std::io::Write;
use std::process::ExitCode;
use std::time::Duration;

use stillair_core::console;
use stillair_core::mcf8316::reg;

mod link;
mod sim;

use link::{field, Link, SerialLink};
use sim::Simulator;

/// How long to wait for a reply to a command before calling the link dead.
const REPLY_TIMEOUT: Duration = Duration::from_secs(2);

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    match run(&arguments) {
        Ok(()) => ExitCode::SUCCESS,
        // Piping into `head` is ordinary usage, not a failure of the run.
        Err(message) if message.contains("Broken pipe") => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("stillair: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run(arguments: &[String]) -> Result<(), String> {
    let mut arguments = arguments.iter().map(String::as_str).peekable();
    let mut link: Option<Box<dyn Link>> = None;

    while let Some(argument) = arguments.peek() {
        match *argument {
            "--sim" => {
                arguments.next();
                link = Some(Box::new(Simulator::new()));
            }
            "--port" => {
                arguments.next();
                let path = arguments.next().ok_or("--port needs a device path")?;
                link = Some(Box::new(
                    SerialLink::open(path).map_err(|error| error.to_string())?,
                ));
            }
            "--help" | "-h" => {
                usage();
                return Ok(());
            }
            _ => break,
        }
    }

    let rest: Vec<&str> = arguments.collect();
    if rest.is_empty() {
        usage();
        return Err("no command given".into());
    }
    let mut link = link.ok_or("choose a target: --sim or --port <device>")?;

    if rest[0] == "script" {
        return script(link.as_mut(), rest.get(1).copied().unwrap_or("-"));
    }
    step(link.as_mut(), &rest)
}

/// Consume anything already queued on the link.
///
/// Without this, a reply left behind by a previous step — the `stream off` ack that `wait`
/// sends on its way out, say — is picked up as the answer to the *next* command, and every
/// reply in a script shifts by one. That misattribution is worse than a missing reply: the
/// script keeps running and reports the wrong register's value as the right one.
fn drain(link: &mut dyn Link) {
    while let Ok(Some(_)) = link.receive(Duration::from_millis(20)) {}
}

/// Run one step: a host command, or anything else passed through to the device.
fn step(link: &mut dyn Link, words: &[&str]) -> Result<(), String> {
    drain(link);
    match words[0] {
        "wait" => wait(link, &words[1..]),
        // `stream on 10` / `stream off` are the device's own syntax and must reach it; the
        // host verb is `stream <hz>`, distinguished by its argument being a number.
        "stream" if !matches!(words.get(1), Some(&"on") | Some(&"off")) => {
            stream(link, &words[1..])
        }
        // `config capture` is a host verb, and `config dump` needs host-side collection
        // because it is the one device command whose reply is many lines rather than one.
        // `config check` and `config apply` are single-reply and pass straight through.
        "config" if words.get(1) == Some(&"capture") => capture(link),
        "config" if words.get(1) == Some(&"dump") => dump(link),
        // Everything else goes to the device verbatim, so the CLI never has to grow a case
        // for a console command it does not need to interpret.
        _ => passthrough(link, &words.join(" ")),
    }
}

/// Run a sequence of steps against **one** session.
///
/// This is what makes the harness usable for anything beyond a single command. Each
/// invocation of the CLI otherwise opens a fresh link — and against `--sim`, a fresh link is
/// a fresh simulator that has forgotten everything, so a two-command sequence would silently
/// test nothing. Commissioning steps are sequences by nature: boot, arm, run, wait, measure.
///
/// Lines are the same commands accepted on the command line. `#` comments and blank lines
/// are ignored. A failing step stops the run and fails, unless prefixed with `-`.
fn script(link: &mut dyn Link, path: &str) -> Result<(), String> {
    let source = if path == "-" {
        std::io::read_to_string(std::io::stdin()).map_err(|error| error.to_string())?
    } else {
        std::fs::read_to_string(path).map_err(|error| format!("{path}: {error}"))?
    };

    for (number, raw) in source.lines().enumerate() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }
        let (line, optional) = match line.strip_prefix('-') {
            Some(rest) => (rest.trim(), true),
            None => (line, false),
        };
        let words: Vec<&str> = line.split_whitespace().collect();
        if words.is_empty() {
            continue;
        }

        eprintln!("# {line}");
        match step(link, &words) {
            Ok(()) => {}
            Err(error) if optional => eprintln!("# (ignored) {error}"),
            Err(error) => return Err(format!("line {}: {line}: {error}", number + 1)),
        }
    }
    Ok(())
}

fn usage() {
    eprintln!("usage: stillair (--sim | --port <device>) <command>");
    eprintln!();
    eprintln!("host commands:");
    eprintln!("  wait <state> [--for <secs>]   block until the fan reaches a state");
    eprintln!("  stream <hz> [--for <secs>]    telemetry as CSV on stdout");
    eprintln!("      (`stream on <hz>`/`stream off` pass through to the device instead)");
    eprintln!("  config capture                print the device's config block as an IMAGE table");
    eprintln!("  script <file|->               run a sequence against one session");
    eprintln!();
    eprintln!("device commands (passed through):");
    for line in console::HELP {
        eprintln!("  {line}");
    }
}

/// Send one request and print its reply.
fn passthrough(link: &mut dyn Link, request: &str) -> Result<(), String> {
    link.send(request).map_err(|error| error.to_string())?;
    let reply = link
        .receive(REPLY_TIMEOUT)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| format!("no reply from {}", link.describe()))?;
    println!("{reply}");
    // A device-reported failure is a failure of the command, and the exit code must say so
    // or a script will march happily past a step that did not happen.
    if field(&reply, "ok") == Some("false") {
        // A configuration verdict carries `detail` rather than `error`; without the fallback
        // a failed `config check` exits non-zero with the useless message "command failed",
        // which is the one moment you want to be told what is actually wrong.
        return Err(field(&reply, "error")
            .or_else(|| field(&reply, "detail"))
            .unwrap_or("command failed")
            .to_string());
    }
    Ok(())
}

/// Block until the fan reports a given state, or fail.
///
/// This is what makes a tuning script sequential: `run 60` returns the instant the target is
/// set, long before the ramp arrives, so anything that needs the fan to actually be there
/// has to wait for it.
fn wait(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let wanted = arguments.first().ok_or("wait needs a state name")?;
    let seconds = flag(arguments, "--for")?.unwrap_or(60);

    link.send("stream on 20").map_err(|e| e.to_string())?;
    // Deadlines run on the link's clock, not ours: against the simulator "30 seconds" means
    // thirty simulated seconds, which arrive in milliseconds.
    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let step = Duration::from_millis(250);
    let mut last = String::new();

    while link.elapsed() < deadline {
        if let Some(line) = link.receive(step).map_err(|e| e.to_string())? {
            if field(&line, "type") != Some("telemetry") {
                continue;
            }
            last = line.clone();
            if field(&line, "state") == Some(*wanted) {
                stop_stream(link);
                println!("{line}");
                return Ok(());
            }
            // A fault will never become the state being waited for; say so immediately
            // rather than burning the whole timeout.
            if field(&line, "state") == Some("fault") && *wanted != "fault" {
                stop_stream(link);
                println!("{line}");
                return Err(format!(
                    "faulted while waiting for {wanted}: {}",
                    field(&line, "fault").unwrap_or("unknown")
                ));
            }
        }
    }

    stop_stream(link);
    Err(format!(
        "timed out after {seconds}s waiting for {wanted}; last state {}",
        field(&last, "state").unwrap_or("unknown")
    ))
}

/// Stream telemetry as CSV on stdout.
fn stream(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let hz: u32 = arguments
        .first()
        .ok_or("stream needs a rate in Hz")?
        .parse()
        .map_err(|_| "stream rate must be a number")?;
    let seconds = flag(arguments, "--for")?.unwrap_or(10);

    link.send(&format!("stream on {hz}"))
        .map_err(|e| e.to_string())?;

    let mut out = std::io::stdout().lock();
    writeln!(
        out,
        "t_ms,state,fault,on,tgt_mrpm,cmd_mrpm,fg_mrpm,hall_mrpm,duty,dir,req_dir,min_mrpm,config,dropped"
    )
    .map_err(|e| e.to_string())?;

    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let step = Duration::from_millis(250);
    let mut frames = 0u64;

    while link.elapsed() < deadline {
        if let Some(line) = link.receive(step).map_err(|e| e.to_string())? {
            if field(&line, "type") != Some("telemetry") {
                continue;
            }
            let column = |key: &str| field(&line, key).unwrap_or("").to_string();
            writeln!(
                out,
                "{},{},{},{},{},{},{},{},{},{},{},{},{},{}",
                column("t"),
                column("state"),
                column("fault"),
                column("on"),
                column("tgt_mrpm"),
                column("cmd_mrpm"),
                column("fg_mrpm"),
                column("hall_mrpm"),
                column("duty"),
                column("dir"),
                column("req_dir"),
                column("min_mrpm"),
                column("config"),
                column("dropped"),
            )
            .map_err(|e| e.to_string())?;
            frames += 1;
        }
    }

    stop_stream(link);
    if frames == 0 {
        return Err(format!("no telemetry from {}", link.describe()));
    }
    Ok(())
}

/// Read the whole EEPROM configuration block off the device.
///
/// `config dump` is the one device command that answers with many lines rather than one, so it
/// cannot go through `passthrough`: that reads a single reply, so it would print the first
/// register of twenty-four and exit zero, reporting a complete dump that never happened.
///
/// The expected register list comes from `stillair-core`, the same source the firmware
/// iterates, so a dump cut short by a bus error fails here rather than arriving silently
/// short — and an image built from a short dump would verify only the part that turned up.
fn read_config_block(link: &mut dyn Link) -> Result<Vec<(String, u16, u32)>, String> {
    let expected: Vec<(&str, u16)> = reg::configuration().collect();
    link.send("config dump").map_err(|e| e.to_string())?;

    let mut values: Vec<(String, u16, u32)> = Vec::new();
    loop {
        let line = link
            .receive(REPLY_TIMEOUT)
            .map_err(|e| e.to_string())?
            .ok_or_else(|| format!("no reply from {}", link.describe()))?;
        if field(&line, "ok") == Some("false") {
            return Err(field(&line, "error").unwrap_or("dump failed").to_string());
        }
        // A telemetry stream left running on the device would otherwise be mistaken for the
        // closing acknowledgement and truncate the block.
        if field(&line, "type") == Some("telemetry") {
            continue;
        }
        let (Some(address), Some(value)) = (field(&line, "addr"), field(&line, "value")) else {
            break; // The closing `{"ok":true}`.
        };
        let address: u16 = address
            .parse()
            .map_err(|_| format!("bad address: {line}"))?;
        let value: u32 = value.parse().map_err(|_| format!("bad value: {line}"))?;
        let name = field(&line, "name").unwrap_or("").to_string();
        values.push((name, address, value));
    }

    if values.len() != expected.len() {
        return Err(format!(
            "expected {} configuration registers, got {} — the dump was cut short, and \
             anything built from it would cover only the part that arrived",
            expected.len(),
            values.len()
        ));
    }
    for ((_, wanted), (_, got, _)) in expected.iter().zip(&values) {
        if wanted != got {
            return Err(format!("expected register {wanted:#05x}, got {got:#05x}"));
        }
    }
    Ok(values)
}

/// Print the device's configuration block, one register per line.
fn dump(link: &mut dyn Link) -> Result<(), String> {
    for (name, address, value) in read_config_block(link)? {
        println!("{address:#05x} {name:<24} {value:#010x}");
    }
    Ok(())
}

/// Print the device's configuration block as a paste-ready `mcf_config::IMAGE` table.
fn capture(link: &mut dyn Link) -> Result<(), String> {
    println!("pub const IMAGE: &[Setting] = &[");
    for (name, address, value) in read_config_block(link)? {
        println!("    Setting::whole(\"{name}\", {address:#05x}, {value:#010x}),");
    }
    println!("];");
    Ok(())
}

/// Stop a telemetry stream and swallow everything still in flight, so the next step starts
/// from a quiet link.
fn stop_stream(link: &mut dyn Link) {
    let _ = link.send("stream off");
    drain(link);
}

/// Read a `--flag <number>` out of the argument list.
///
/// Three outcomes, deliberately distinct: absent, present and valid, present and broken. A
/// mistyped `--for 36000o` must not silently become the default — a capture that was meant
/// to run for ten hours and quietly ran for ten seconds still exits zero, and the truncated
/// CSV looks like a complete one.
fn flag(arguments: &[&str], name: &str) -> Result<Option<u64>, String> {
    let Some(index) = arguments.iter().position(|argument| *argument == name) else {
        return Ok(None);
    };
    let value = arguments
        .get(index + 1)
        .ok_or_else(|| format!("{name} needs a value"))?;
    value
        .parse()
        .map(Some)
        .map_err(|_| format!("{name} needs a number, got {value:?}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;

    #[test]
    fn flags_are_read_by_name() {
        let arguments = ["10", "--for", "120"];
        assert_eq!(flag(&arguments, "--for"), Ok(Some(120)));
        assert_eq!(flag(&arguments, "--missing"), Ok(None));
    }

    #[test]
    fn a_broken_flag_value_is_an_error_not_a_silent_default() {
        assert!(flag(&["--for"], "--for").is_err(), "a flag with no value");
        assert!(flag(&["--for", "36000o"], "--for").is_err(), "a typo");
        // And it reaches the caller rather than being swallowed into the default.
        let mut sim = Simulator::new();
        assert!(stream(&mut sim, &["20", "--for", "x"]).is_err());
    }

    #[test]
    fn a_device_reported_failure_becomes_a_nonzero_exit() {
        let mut sim = Simulator::new();
        let result = passthrough(&mut sim, "frobnicate");
        assert_eq!(result, Err("unknown command".to_string()));
    }

    #[test]
    fn a_successful_command_succeeds() {
        let mut sim = Simulator::new();
        assert!(passthrough(&mut sim, "stop").is_ok());
    }

    #[test]
    fn waiting_for_a_reachable_state_succeeds() {
        let mut sim = Simulator::new();
        assert!(wait(&mut sim, &["idle_off", "--for", "30"]).is_ok());
    }

    #[test]
    fn waiting_times_out_rather_than_hanging() {
        let mut sim = Simulator::new();
        // Nothing commands a start, so `running` never arrives.
        let result = wait(&mut sim, &["running", "--for", "20"]);
        assert!(result.is_err(), "wait should have timed out");
        assert!(result.unwrap_err().contains("timed out"));
    }

    #[test]
    fn the_device_stream_syntax_is_not_swallowed_by_the_host_verb() {
        // `stream off` is a device command; routing it to the host handler would fail with
        // "stream rate must be a number" even though the help text advertises it.
        let mut sim = Simulator::new();
        assert!(step(&mut sim, &["stream", "off"]).is_ok());
        assert!(step(&mut sim, &["stream", "on", "10"]).is_ok());
    }

    #[test]
    fn a_script_runs_its_steps_against_one_session() {
        // The whole point: state set by an early step is still there for a later one.
        let mut sim = Simulator::new();
        let source = "\
# boot, then prove a register write is visible to a later step
wait idle_off --for 30
reg write ISD_CONFIG 0x12345678
reg read ISD_CONFIG
";
        let path = std::env::temp_dir().join("stillair-script-test.txt");
        std::fs::write(&path, source).unwrap();
        assert!(script(&mut sim, path.to_str().unwrap()).is_ok());

        // Confirm the value really persisted across steps.
        sim.send("reg read ISD_CONFIG").unwrap();
        let reply = sim.receive(Duration::from_millis(10)).unwrap().unwrap();
        assert_eq!(field(&reply, "value"), Some("305419896"));
    }

    #[test]
    fn replies_are_not_shifted_by_a_previous_steps_leftovers() {
        // A `wait` leaves a `stream off` ack behind. If it is not drained, the next step's
        // reply is the previous step's, and a register read reports the wrong value.
        let mut sim = Simulator::new();
        let path = std::env::temp_dir().join("stillair-script-shift.txt");
        std::fs::write(
            &path,
            "wait idle_off --for 30\nreg write ISD_CONFIG 0xAABBCCDD\n",
        )
        .unwrap();
        assert!(script(&mut sim, path.to_str().unwrap()).is_ok());

        drain(&mut sim);
        sim.send("reg read ISD_CONFIG").unwrap();
        let reply = sim.receive(Duration::from_millis(50)).unwrap().unwrap();
        assert_eq!(
            field(&reply, "value"),
            Some(0xAABB_CCDDu32.to_string().as_str()),
            "the write did not land, or its reply was misattributed"
        );
    }

    #[test]
    fn a_failing_script_step_stops_the_run() {
        let mut sim = Simulator::new();
        let path = std::env::temp_dir().join("stillair-script-fail.txt");
        std::fs::write(&path, "frobnicate\nstop\n").unwrap();
        let result = script(&mut sim, path.to_str().unwrap());
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("unknown command"));
    }

    #[test]
    fn an_optional_script_step_may_fail_without_stopping_the_run() {
        let mut sim = Simulator::new();
        let path = std::env::temp_dir().join("stillair-script-optional.txt");
        std::fs::write(&path, "- frobnicate\nstop\n").unwrap();
        assert!(script(&mut sim, path.to_str().unwrap()).is_ok());
    }

    #[test]
    fn comments_and_blank_lines_are_skipped() {
        let mut sim = Simulator::new();
        let path = std::env::temp_dir().join("stillair-script-comments.txt");
        std::fs::write(&path, "# just a comment\n\n   \nstop # trailing\n").unwrap();
        assert!(script(&mut sim, path.to_str().unwrap()).is_ok());
    }

    #[test]
    fn a_config_dump_is_collected_whole_rather_than_one_line_deep() {
        // `passthrough` reads exactly one reply. Routing `config dump` through it printed
        // the first register of twenty-four and exited zero — a complete-looking dump that
        // never happened, which is the failure mode this harness exists to not have.
        let mut sim = Simulator::new();
        let block = read_config_block(&mut sim).expect("a whole block");
        assert_eq!(block.len(), reg::configuration().count());
        assert_eq!(block.first().unwrap().1, reg::CONFIG_FIRST);
        assert_eq!(block.last().unwrap().1, reg::CONFIG_LAST);
    }

    #[test]
    fn a_short_config_dump_fails_rather_than_producing_a_partial_image() {
        // A link that answers the dump with two registers and then the closing ack, as a
        // bus error mid-block would. An image built from that would verify a quarter of the
        // configuration and silently vouch for the rest.
        struct ShortDump {
            replies: VecDeque<String>,
        }
        impl Link for ShortDump {
            fn send(&mut self, _: &str) -> std::io::Result<()> {
                self.replies = [
                    "{\"ok\":true,\"addr\":128,\"name\":\"ISD_CONFIG\",\"value\":1}",
                    "{\"ok\":true,\"addr\":130,\"name\":\"REV_DRIVE_CONFIG\",\"value\":2}",
                    "{\"ok\":true}",
                ]
                .iter()
                .map(|line| line.to_string())
                .collect();
                Ok(())
            }
            fn receive(&mut self, _: Duration) -> std::io::Result<Option<String>> {
                Ok(self.replies.pop_front())
            }
            fn describe(&self) -> String {
                "short-dump".into()
            }
            fn elapsed(&self) -> Duration {
                Duration::ZERO
            }
        }

        let mut link = ShortDump {
            replies: VecDeque::new(),
        };
        let error = read_config_block(&mut link).expect_err("a short dump must fail");
        assert!(error.contains("cut short"), "{error}");
        assert!(capture(&mut link).is_err());
    }

    #[test]
    fn streaming_produces_a_csv_with_a_header_and_rows() {
        // Exercised through the simulator so the whole path is covered; the row count is
        // checked via the frame counter rather than by capturing stdout.
        let mut sim = Simulator::new();
        assert!(stream(&mut sim, &["20", "--for", "5"]).is_ok());
    }
}
