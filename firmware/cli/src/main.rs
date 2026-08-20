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

use stillair_core::config;
use stillair_core::console;
use stillair_core::mcf8316::{max_speed_to_milli_rpm, reg, seeds};

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
        "dwell" => dwell(link, &words[1..]),
        "wait" if words.get(1) == Some(&"speed") => wait_speed(link, &words[2..]),
        "wait" => wait(link, &words[1..]),
        // `stream on 10` / `stream off` are the device's own syntax and must reach it; the
        // host verb is `stream <hz>`, distinguished by its argument being a number.
        "stream" if !matches!(words.get(1), Some(&"on") | Some(&"off")) => {
            stream(link, &words[1..])
        }
        "speed" if words.get(1) == Some(&"sample") => sample_speed(link, &words[2..]),
        "estimator" if words.get(1) == Some(&"sample") => sample_estimator(link, &words[2..]),
        // `config capture` is a host verb, and `config dump` needs host-side collection
        // because it is the one device command whose reply is many lines rather than one.
        // `config check`, `config stage`, and `config apply` are single-reply and pass
        // straight through.
        "config" if words.get(1) == Some(&"capture") => capture(link),
        "config" if words.get(1) == Some(&"dump") => dump(link),
        "mpet" if words.get(1) == Some(&"run") => mpet_run(link, &words[2..]),
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

    let started = link.elapsed();
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

        eprintln!(
            "# t={:.3}s {line}",
            (link.elapsed() - started).as_secs_f64()
        );
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
    eprintln!("  dwell <secs>                  hold the current command with 1 Hz monitoring");
    eprintln!("  wait <state> [--for <secs>]   block until the fan reaches a state");
    eprintln!("  wait speed <rpm> [--within <rpm>] [--for <secs>]");
    eprintln!("  stream <hz> [--for <secs>]    telemetry as CSV on stdout");
    eprintln!("      (`stream on <hz>`/`stream off` pass through to the device instead)");
    eprintln!("  speed sample [--for <secs>]   live MCF speed feedback as CSV");
    eprintln!("  estimator sample [--for <secs>] [--interval-ms <ms>]  angle/current trace as CSV");
    eprintln!("  config capture                print the device's config block as an IMAGE table");
    eprintln!("  mpet run [--electrical] [--for <secs>]  run MPET safely, report, then disarm");
    eprintln!("  script <file|->               run a sequence against one session");
    eprintln!();
    eprintln!("device commands (passed through):");
    for line in console::HELP {
        eprintln!("  {line}");
    }
}

/// Hold the current device command for a fixed interval while watching for faults.
///
/// A speed-arrival gate proves that a ramp crossed its target, not that the motor stayed
/// there. A one-hertz stream gives physical camera and power logging a real plateau without
/// recreating the high-rate serial pressure of an estimator capture.
fn dwell(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let seconds: u64 = arguments
        .first()
        .ok_or("dwell needs a duration in seconds")?
        .parse()
        .map_err(|_| "dwell duration must be a number")?;
    if seconds == 0 {
        return Err("dwell duration must be greater than zero".into());
    }

    link.send("stream on 1")
        .map_err(|error| error.to_string())?;
    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let mut last = None;
    let mut last_telemetry_at = link.elapsed();
    while link.elapsed() < deadline {
        let received = link
            .receive(Duration::from_millis(250))
            .map_err(|error| error.to_string())?;
        if let Some(line) = received {
            if field(&line, "type") != Some("telemetry") {
                continue;
            }
            last_telemetry_at = link.elapsed();
            if field(&line, "state") == Some("fault") {
                let _ = stop_stream(link);
                return Err(format!(
                    "faulted during {seconds}s dwell: {}",
                    field(&line, "fault").unwrap_or("unknown")
                ));
            }
            if field(&line, "state") != Some("running") || field(&line, "on") != Some("true") {
                let state = field(&line, "state").unwrap_or("unknown");
                let _ = stop_stream(link);
                return Err(format!(
                    "left running state during {seconds}s dwell: {state}"
                ));
            }
            last = Some(line);
        } else if link.elapsed().saturating_sub(last_telemetry_at) > Duration::from_secs(3) {
            let _ = stop_stream(link);
            return Err(format!("no telemetry heartbeat during {seconds}s dwell"));
        }
    }
    stop_stream(link)?;
    let line = last.ok_or_else(|| format!("no telemetry during {seconds}s dwell"))?;
    println!("{line}");
    Ok(())
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
                stop_stream(link)?;
                println!("{line}");
                return Ok(());
            }
            // A fault will never become the state being waited for; say so immediately
            // rather than burning the whole timeout.
            if field(&line, "state") == Some("fault") && *wanted != "fault" {
                let _ = stop_stream(link);
                println!("{line}");
                return Err(format!(
                    "faulted while waiting for {wanted}: {}",
                    field(&line, "fault").unwrap_or("unknown")
                ));
            }
        }
    }

    let _ = stop_stream(link);
    Err(format!(
        "timed out after {seconds}s waiting for {wanted}; last state {}",
        field(&last, "state").unwrap_or("unknown")
    ))
}

/// Wait for three consecutive FG measurements around a target. A single sample is too easy
/// to satisfy during a ramp; Hall remains in the CSV as an independent diagnostic but is too
/// coarse at low speed to be the arrival gate.
fn wait_speed(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let wanted_rpm: u32 = arguments
        .first()
        .ok_or("wait speed needs an RPM")?
        .parse()
        .map_err(|_| "wait speed RPM must be a number")?;
    let within_rpm = flag(arguments, "--within")?.unwrap_or(3);
    let seconds = flag(arguments, "--for")?.unwrap_or(120);
    let wanted = u64::from(wanted_rpm) * 1_000;
    let tolerance = within_rpm
        .checked_mul(1_000)
        .ok_or_else(|| "--within is too large".to_string())?;

    link.send("stream on 10")
        .map_err(|error| error.to_string())?;
    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let mut consecutive = 0;
    let mut last = String::new();
    while link.elapsed() < deadline {
        if let Some(line) = link
            .receive(Duration::from_millis(250))
            .map_err(|error| error.to_string())?
        {
            if field(&line, "type") != Some("telemetry") {
                continue;
            }
            last = line.clone();
            if field(&line, "state") == Some("fault") {
                let _ = stop_stream(link);
                return Err(format!(
                    "faulted while waiting for {wanted_rpm} rpm: {}",
                    field(&line, "fault").unwrap_or("unknown")
                ));
            }
            let measured = field(&line, "fg_mrpm")
                .ok_or("telemetry omitted fg_mrpm")?
                .parse::<u64>()
                .map_err(|_| "telemetry carried invalid fg_mrpm")?;
            let commanded = field(&line, "cmd_mrpm")
                .ok_or("telemetry omitted cmd_mrpm")?
                .parse::<u64>()
                .map_err(|_| "telemetry carried invalid cmd_mrpm")?;
            if measured.abs_diff(wanted) <= tolerance && commanded.abs_diff(wanted) <= tolerance {
                consecutive += 1;
                if consecutive == 3 {
                    stop_stream(link)?;
                    println!("{line}");
                    return Ok(());
                }
            } else {
                consecutive = 0;
            }
        }
    }
    let _ = stop_stream(link);
    Err(format!(
        "timed out after {seconds}s waiting for {wanted_rpm} +/- {within_rpm} rpm; last command {} mrpm, FG {} mrpm",
        field(&last, "cmd_mrpm").unwrap_or("unknown"),
        field(&last, "fg_mrpm").unwrap_or("unknown"),
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

    stop_stream(link)?;
    if frames == 0 {
        return Err(format!("no telemetry from {}", link.describe()));
    }
    Ok(())
}

/// Sample the MCF's internal speed estimator as quickly as the I2C service allows.
///
/// FG and rotor-Hall telemetry are necessarily sparse at first-spin speeds. `SPEED_FDBK`
/// is the controller's live estimate, so a dense capture exposes speed ripple during the
/// open-loop handoff ramp instead of asking a person to judge jitter by eye.
fn sample_speed(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let seconds = flag(arguments, "--for")?.unwrap_or(10);
    let max_mrpm = i64::from(max_speed_to_milli_rpm(seeds::MAX_SPEED, config::POLE_PAIRS).0);
    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let mut total_samples = 0u64;
    let mut tracking_samples = 0u64;
    let mut mean = 0.0f64;
    let mut sum_squared_delta = 0.0f64;
    let mut minimum_error = i64::MAX;
    let mut maximum_error = i64::MIN;
    let mut maximum_absolute_error = 0i64;
    let mut out = std::io::stdout().lock();
    writeln!(
        out,
        "t_ms,algorithm_state,open_ref_raw,closed_ref_raw,feedback_raw,open_ref_mrpm,closed_ref_mrpm,active_ref_mrpm,feedback_mrpm,error_mrpm,controller_fault"
    )
    .map_err(|error| error.to_string())?;

    while link.elapsed() < deadline {
        let algorithm_state = read_register(link, "ALGORITHM_STATE")?;
        let reference_raw = read_register(link, "SPEED_REF_OPEN_LOOP")?;
        let closed_reference_raw = read_register(link, "SPEED_REF_CLOSED_LOOP")?;
        let feedback_raw = read_register(link, "SPEED_FDBK")?;
        let controller_fault = read_register(link, "CONTROLLER_FAULT_STATUS")?;
        let reference_mrpm = q27_speed_mrpm(reference_raw, max_mrpm);
        let closed_reference_mrpm = q27_speed_mrpm(closed_reference_raw, max_mrpm);
        let feedback_mrpm = q27_speed_mrpm(feedback_raw, max_mrpm);
        let active_reference =
            active_speed_reference(algorithm_state, reference_mrpm, closed_reference_mrpm);
        let error = active_reference
            .map(|reference| feedback_mrpm.abs() - reference.abs())
            .unwrap_or(0);
        if active_reference.is_some_and(|reference| reference.abs() >= 5_000)
            && controller_fault == 0
        {
            minimum_error = minimum_error.min(error);
            maximum_error = maximum_error.max(error);
            maximum_absolute_error = maximum_absolute_error.max(error.abs());
            let value = error as f64;
            let delta = value - mean;
            mean += delta / (tracking_samples + 1) as f64;
            sum_squared_delta += delta * (value - mean);
            tracking_samples += 1;
        }
        writeln!(
            out,
            "{},{algorithm_state},{reference_raw},{closed_reference_raw},{feedback_raw},{reference_mrpm},{closed_reference_mrpm},{},{feedback_mrpm},{error},{controller_fault}",
            link.elapsed().as_millis(),
            active_reference.unwrap_or(0),
        )
        .map_err(|error| error.to_string())?;
        total_samples += 1;
    }

    if tracking_samples == 0 {
        return Err(format!("no SPEED_FDBK samples from {}", link.describe()));
    }
    let stddev = (sum_squared_delta / tracking_samples as f64).sqrt();
    writeln!(
        out,
        "{{\"type\":\"speed_tracking_summary\",\"samples\":{total_samples},\
         \"tracking_samples\":{tracking_samples},\
         \"mean_error_mrpm\":{mean:.0},\"min_error_mrpm\":{minimum_error},\
         \"max_error_mrpm\":{maximum_error},\"max_abs_error_mrpm\":{maximum_absolute_error},\
         \"stddev_error_mrpm\":{stddev:.0}}}",
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

/// Capture the signals that distinguish observer loss from speed-loop or current-loop loss.
///
/// These are deliberately read in the same order on every pass. The serial console adds
/// more latency than the MCF I2C reads, but a single row still brackets the sub-second
/// open-to-closed-loop transition without asking a person to infer it from motion.
fn sample_estimator(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let seconds = flag(arguments, "--for")?.unwrap_or(10);
    let interval_ms = flag(arguments, "--interval-ms")?.unwrap_or(500);
    if !(50..=5_000).contains(&interval_ms) {
        return Err("--interval-ms must be between 50 and 5000".into());
    }
    let max_mrpm = i64::from(max_speed_to_milli_rpm(seeds::MAX_SPEED, config::POLE_PAIRS).0);
    let deadline = link.elapsed() + Duration::from_secs(seconds);
    let mut samples = 0u64;
    let mut max_abs_iq_ref_ma = 0i64;
    let mut max_abs_iq_ma = 0i64;
    let mut previous_transition_speed: Option<i64> = None;
    let mut transition_decelerations = 0u64;
    let mut direction_reversals = 0u64;
    let mut dropped_samples = 0u64;
    let mut consecutive_drops = 0u64;
    let mut out = std::io::stdout().lock();
    writeln!(
        out,
        "t_ms,algorithm_state,speed_raw,open_iq_ref_raw,closed_iq_ref_raw,id_raw,iq_raw,vd_raw,vq_raw,theta_raw,ed_raw,eq_raw,algo_status_raw,vm_raw,speed_mrpm,open_iq_ref_ma,closed_iq_ref_ma,id_ma,iq_ma,vd_mv,vq_mv,theta_mdeg,ed_mv,eq_mv,ke_mv_per_ehz,modulation_per_mille,vm_mv,fg_mrpm,hall_mrpm,controller_fault"
    )
    .map_err(|error| error.to_string())?;

    while link.elapsed() < deadline {
        let row = (|| {
            let registers = (
                read_register(link, "ALGORITHM_STATE")?,
                read_register(link, "SPEED_FDBK")?,
                read_register(link, "IQ_REF_OPEN_LOOP")?,
                read_register(link, "IQ_REF_CLOSED_LOOP")?,
                read_register(link, "ID")?,
                read_register(link, "IQ")?,
                read_register(link, "VD")?,
                read_register(link, "VQ")?,
                read_register(link, "THETA_EST")?,
                read_register(link, "ED")?,
                read_register(link, "EQ")?,
                read_register(link, "ALGO_STATUS")?,
                read_register(link, "VM_VOLTAGE")?,
                read_register(link, "CONTROLLER_FAULT_STATUS")?,
            );
            let (fg_mrpm, hall_mrpm) = read_tach_telemetry(link)?;
            Ok::<_, String>((registers, fg_mrpm, hall_mrpm))
        })();
        let (
            (
                algorithm_state,
                speed_raw,
                open_iq_ref_raw,
                iq_ref_raw,
                id_raw,
                iq_raw,
                vd_raw,
                vq_raw,
                theta_raw,
                ed_raw,
                eq_raw,
                algo_status_raw,
                vm_raw,
                controller_fault,
            ),
            fg_mrpm,
            hall_mrpm,
        ) = match row {
            Ok(row) => row,
            Err(error) => {
                dropped_samples += 1;
                consecutive_drops += 1;
                eprintln!("estimator sample dropped: {error}");
                if consecutive_drops >= 3 {
                    return Err(format!(
                        "estimator link failed {consecutive_drops} consecutive rows on {}",
                        link.describe()
                    ));
                }
                continue;
            }
        };
        consecutive_drops = 0;
        let speed_mrpm = q27_speed_mrpm(speed_raw, max_mrpm);
        let open_iq_ref_ma = q27_scaled(open_iq_ref_raw, 1_250);
        let iq_ref_ma = q27_scaled(iq_ref_raw, 1_250);
        let id_ma = q27_scaled(id_raw, 1_250);
        let iq_ma = q27_scaled(iq_raw, 1_250);
        let vd_mv = q27_scaled(vd_raw, 34_641);
        let vq_mv = q27_scaled(vq_raw, 34_641);
        let theta_mdeg = q27_scaled(theta_raw, 360_000);
        let ed_mv = q27_scaled(ed_raw, 34_641);
        let eq_mv = q27_scaled(eq_raw, 34_641);
        let ke_mv_per_ehz = if speed_mrpm == 0 {
            0
        } else {
            eq_mv.abs() * 60_000 / (speed_mrpm.abs() * i64::from(config::POLE_PAIRS))
        };
        let modulation_per_mille = i64::from(algo_status_raw >> 16) * 1_000 / 32_768;
        let vm_mv = q27_scaled(vm_raw, 60_000);
        if controller_fault == 0 {
            max_abs_iq_ref_ma = max_abs_iq_ref_ma.max(iq_ref_ma.abs());
            max_abs_iq_ma = max_abs_iq_ma.max(iq_ma.abs());
            if matches!(algorithm_state, 7 | 8) {
                if let Some(previous) = previous_transition_speed {
                    if previous.signum() != speed_mrpm.signum()
                        && previous.abs() >= 1_000
                        && speed_mrpm.abs() >= 1_000
                    {
                        direction_reversals += 1;
                    }
                    if previous.abs() - speed_mrpm.abs() >= 2_000 {
                        transition_decelerations += 1;
                    }
                }
                previous_transition_speed = Some(speed_mrpm);
            }
        }
        writeln!(
            out,
            "{},{algorithm_state},{speed_raw},{open_iq_ref_raw},{iq_ref_raw},{id_raw},{iq_raw},{vd_raw},{vq_raw},{theta_raw},{ed_raw},{eq_raw},{algo_status_raw},{vm_raw},{speed_mrpm},{open_iq_ref_ma},{iq_ref_ma},{id_ma},{iq_ma},{vd_mv},{vq_mv},{theta_mdeg},{ed_mv},{eq_mv},{ke_mv_per_ehz},{modulation_per_mille},{vm_mv},{fg_mrpm},{hall_mrpm},{controller_fault}",
            link.elapsed().as_millis()
        )
        .map_err(|error| error.to_string())?;
        samples += 1;
        // Do not saturate the USB console and I2C service with an unbroken request burst.
        let _ = link.receive(Duration::from_millis(interval_ms));
    }

    writeln!(
        out,
        "{{\"type\":\"estimator_summary\",\"samples\":{samples},\"dropped_samples\":{dropped_samples},\"max_abs_iq_ref_ma\":{max_abs_iq_ref_ma},\"max_abs_iq_ma\":{max_abs_iq_ma},\"transition_decelerations\":{transition_decelerations},\"direction_reversals\":{direction_reversals}}}"
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

fn read_tach_telemetry(link: &mut dyn Link) -> Result<(i64, i64), String> {
    link.send("state").map_err(|error| error.to_string())?;
    for _ in 0..3 {
        let line = link
            .receive(Duration::from_millis(250))
            .map_err(|error| error.to_string())?
            .ok_or("state telemetry timed out")?;
        if field(&line, "type") != Some("telemetry") {
            continue;
        }
        let parse = |key: &str| {
            field(&line, key)
                .ok_or_else(|| format!("state telemetry omitted {key}"))?
                .parse::<i64>()
                .map_err(|_| format!("state telemetry carried invalid {key}"))
        };
        return Ok((parse("fg_mrpm")?, parse("hall_mrpm")?));
    }
    Err("state produced no telemetry frame".into())
}

fn q27_scaled(raw: u32, scale: i64) -> i64 {
    i64::from(raw as i32) * scale / (1_i64 << 27)
}

fn read_register(link: &mut dyn Link, name: &str) -> Result<u32, String> {
    let expected_address = reg::by_name(name).ok_or_else(|| format!("unknown register {name}"))?;
    link.send(&format!("reg read {name}"))
        .map_err(|error| error.to_string())?;
    for _ in 0..3 {
        let reply = link
            .receive(REPLY_TIMEOUT)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| format!("no {name} reply from {}", link.describe()))?;
        if field(&reply, "ok") == Some("false") {
            return Err(field(&reply, "error")
                .unwrap_or("register read failed")
                .to_string());
        }
        let address = field(&reply, "addr").and_then(|value| value.parse::<u16>().ok());
        if address != Some(expected_address) {
            continue;
        }
        return field(&reply, "value")
            .ok_or_else(|| format!("{name} reply omitted value"))?
            .parse()
            .map_err(|_| format!("{name} reply carried an invalid value"));
    }
    Err(format!("no matching {name} reply from {}", link.describe()))
}

fn q27_speed_mrpm(raw: u32, max_mrpm: i64) -> i64 {
    (i64::from(raw as i32) * max_mrpm) / (1_i64 << 27)
}

fn active_speed_reference(algorithm_state: u32, open_mrpm: i64, closed_mrpm: i64) -> Option<i64> {
    // MCF8316D ALGORITHM_STATE: 7 is open loop, 8/9 are closed-loop unaligned/aligned.
    // Stopping and fault states are deliberately excluded from tracking statistics.
    match algorithm_state {
        7 => Some(open_mrpm),
        8 | 9 => Some(closed_mrpm),
        _ => None,
    }
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

/// Run motor-parameter extraction as one bounded service operation.
///
/// The device owns the permission and fault behavior; the host owns completion polling and
/// the deadline. Results are left in shadow only, so a successful extraction never consumes
/// EEPROM endurance until the operator reviews and explicitly applies a captured image.
fn mpet_run(link: &mut dyn Link, arguments: &[&str]) -> Result<(), String> {
    let seconds = flag(arguments, "--for")?.unwrap_or(120);
    let electrical = arguments.contains(&"--electrical");
    passthrough(
        link,
        if electrical {
            "mpet electrical"
        } else {
            "mpet start"
        },
    )?;
    let completion_mask = if electrical {
        stillair_core::mcf8316::MPET_ELECTRICAL_COMPLETE_MASK
    } else {
        stillair_core::mcf8316::MPET_COMPLETE_MASK
    };
    let result = mpet_session(link, seconds, completion_mask);
    let abort = passthrough(link, "mpet abort");
    result?;
    abort?;
    wait(link, &["idle_off", "--for", "20"])
}

fn mpet_session(link: &mut dyn Link, seconds: u64, completion_mask: u32) -> Result<(), String> {
    wait(link, &["mpet", "--for", "20"])?;

    let deadline = link.elapsed() + Duration::from_secs(seconds);
    while link.elapsed() < deadline {
        drain(link);
        link.send("mpet status")
            .map_err(|error| error.to_string())?;
        let reply = link
            .receive(REPLY_TIMEOUT)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| format!("no MPET status from {}", link.describe()))?;
        if field(&reply, "ok") == Some("false") {
            return Err(field(&reply, "error")
                .unwrap_or("MPET status failed")
                .to_string());
        }
        if field(&reply, "type") != Some("mpet") {
            return Err(format!("expected MPET status, got {reply}"));
        }
        let status = field(&reply, "status")
            .and_then(|value| value.parse::<u32>().ok())
            .ok_or_else(|| format!("MPET status omitted a valid status word: {reply}"))?;
        if status & completion_mask == completion_mask {
            println!("{reply}");
            return Ok(());
        }
        // Advance real or simulated time without leaving a telemetry stream behind.
        let _ = link.receive(Duration::from_millis(250));
    }

    Err(format!("MPET did not complete within {seconds}s"))
}

/// Stop a telemetry stream and require the device to acknowledge it.
fn stop_stream(link: &mut dyn Link) -> Result<(), String> {
    link.send("stream off").map_err(|error| error.to_string())?;
    let deadline = link.elapsed() + REPLY_TIMEOUT;
    while link.elapsed() < deadline {
        let Some(line) = link
            .receive(Duration::from_millis(100))
            .map_err(|error| error.to_string())?
        else {
            continue;
        };
        if field(&line, "type") == Some("telemetry") {
            continue;
        }
        if field(&line, "ok") == Some("true") {
            drain(link);
            return Ok(());
        }
        return Err(field(&line, "error")
            .unwrap_or("stream-off command failed")
            .to_string());
    }
    Err(format!(
        "no stream-off acknowledgement from {}",
        link.describe()
    ))
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

    fn staged_simulator() -> Simulator {
        let mut sim = Simulator::new();
        passthrough(&mut sim, "config stage").expect("stage provisional configuration");
        sim
    }
    use std::collections::VecDeque;

    #[test]
    fn flags_are_read_by_name() {
        let arguments = ["10", "--for", "120"];
        assert_eq!(flag(&arguments, "--for"), Ok(Some(120)));
        assert_eq!(flag(&arguments, "--missing"), Ok(None));
    }

    #[test]
    fn q27_speed_conversion_preserves_direction_and_scale() {
        assert_eq!(q27_speed_mrpm(1 << 26, 180_000), 90_000);
        assert_eq!(q27_speed_mrpm((-67_108_864i32) as u32, 180_000), -90_000);
    }

    #[test]
    fn speed_tracking_uses_the_reference_owned_by_the_algorithm_state() {
        assert_eq!(active_speed_reference(7, 11, 22), Some(11));
        assert_eq!(active_speed_reference(8, 11, 22), Some(22));
        assert_eq!(active_speed_reference(9, 11, 22), Some(22));
        assert_eq!(active_speed_reference(6, 11, 22), None);
        assert_eq!(active_speed_reference(10, 11, 22), None);
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
    fn estimator_interval_is_bounded_before_any_device_access() {
        let mut sim = Simulator::new();
        assert_eq!(
            sample_estimator(&mut sim, &["--interval-ms", "49"]),
            Err("--interval-ms must be between 50 and 5000".into())
        );
        assert_eq!(
            sample_estimator(&mut sim, &["--interval-ms", "5001"]),
            Err("--interval-ms must be between 50 and 5000".into())
        );
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
        let mut sim = staged_simulator();
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
    fn waiting_for_speed_requires_and_detects_arrival() {
        let mut sim = staged_simulator();
        assert!(wait(&mut sim, &["idle_off", "--for", "30"]).is_ok());
        assert!(passthrough(&mut sim, "run 60").is_ok());
        assert!(wait_speed(&mut sim, &["60", "--within", "2", "--for", "120"]).is_ok());
    }

    #[test]
    fn dwell_holds_a_running_command_without_changing_it() {
        let mut sim = staged_simulator();
        assert!(wait(&mut sim, &["idle_off", "--for", "30"]).is_ok());
        assert!(passthrough(&mut sim, "run 60").is_ok());
        assert!(wait_speed(&mut sim, &["60", "--within", "2", "--for", "120"]).is_ok());
        assert!(dwell(&mut sim, &["3"]).is_ok());
        sim.send("state").unwrap();
        let reply = sim.receive(Duration::from_millis(50)).unwrap().unwrap();
        assert_eq!(field(&reply, "state"), Some("running"));
        assert_eq!(field(&reply, "tgt_mrpm"), Some("60000"));
    }

    #[test]
    fn dwell_rejects_missing_zero_and_invalid_durations() {
        let mut sim = Simulator::new();
        assert!(dwell(&mut sim, &[]).is_err());
        assert!(dwell(&mut sim, &["0"]).is_err());
        assert!(dwell(&mut sim, &["later"]).is_err());
    }

    #[test]
    fn dwell_fails_closed_when_telemetry_goes_silent() {
        struct SilentLink {
            elapsed: Duration,
        }

        impl Link for SilentLink {
            fn send(&mut self, _: &str) -> std::io::Result<()> {
                Ok(())
            }

            fn receive(&mut self, timeout: Duration) -> std::io::Result<Option<String>> {
                self.elapsed += timeout;
                Ok(None)
            }

            fn describe(&self) -> String {
                "silent test link".into()
            }

            fn elapsed(&self) -> Duration {
                self.elapsed
            }
        }

        let mut link = SilentLink {
            elapsed: Duration::ZERO,
        };
        let error = dwell(&mut link, &["10"]).expect_err("silent dwell must fail");
        assert!(error.contains("heartbeat"), "{error}");
    }

    #[test]
    fn an_impossible_speed_tolerance_is_rejected_without_overflowing() {
        let mut sim = Simulator::new();
        let too_large = (u64::MAX / 1_000 + 1).to_string();
        assert_eq!(
            wait_speed(&mut sim, &["60", "--within", &too_large]),
            Err("--within is too large".to_string())
        );
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
config stage
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
            "config stage\nwait idle_off --for 30\nreg write ISD_CONFIG 0xAABBCCDD\n",
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

    #[test]
    fn controlled_mpet_completes_and_returns_to_idle() {
        let mut sim = staged_simulator();
        assert!(wait(&mut sim, &["idle_off", "--for", "30"]).is_ok());
        assert!(mpet_run(&mut sim, &["--for", "5"]).is_ok());
        sim.send("state").unwrap();
        let reply = sim.receive(Duration::from_millis(50)).unwrap().unwrap();
        assert_eq!(field(&reply, "state"), Some("idle_off"));
    }

    #[test]
    fn electrical_mpet_completes_and_returns_to_idle() {
        let mut sim = staged_simulator();
        assert!(wait(&mut sim, &["idle_off", "--for", "30"]).is_ok());
        assert!(mpet_run(&mut sim, &["--electrical", "--for", "5"]).is_ok());
        sim.send("state").unwrap();
        let reply = sim.receive(Duration::from_millis(50)).unwrap().unwrap();
        assert_eq!(field(&reply, "state"), Some("idle_off"));
    }

    #[test]
    fn q27_diagnostics_decode_signed_current_and_angle() {
        assert_eq!(q27_scaled(1 << 27, 1_000), 1_000);
        assert_eq!(q27_scaled((-67_108_864_i32) as u32, 1_000), -500);
        assert_eq!(q27_scaled(1 << 26, 360_000), 180_000);
    }
}
