import fs from "node:fs";

import { KlapDiscovery } from "/var/lib/homebridge/node_modules/homebridge-kasa/lib/klap/KlapDiscovery.js";

const EXPECTED = Object.freeze({
  host: "10.10.1.42",
  id: "803ADF1292A1F16E6C4D9595F665756E21250899",
  alias: "Utility Plug",
});

const action = process.argv[2];
const durationSeconds = Number(process.argv[3] ?? "0");
const runId = process.argv[4];
if (!["status", "on", "off", "cycle", "log", "stop-log"].includes(action)) {
  throw new Error(
    "usage: utility_plug_controller.mjs status|on|off|cycle|log [seconds] [run-id]",
  );
}
if (
  action === "log" &&
  (!Number.isInteger(durationSeconds) || durationSeconds < 1 || durationSeconds > 3600)
) {
  throw new Error("log duration must be an integer from 1 through 3600 seconds");
}
if ((action === "log" || action === "stop-log") && !/^\d{8}-\d{6}$/.test(runId ?? "")) {
  throw new Error("log operations require a timestamp run id");
}

const loggerStateDir = "/tmp/stillair-utility-plug";
if (runId) {
  fs.mkdirSync(loggerStateDir, { recursive: true, mode: 0o700 });
  const state = fs.statSync(loggerStateDir);
  if (state.uid !== process.getuid() || (state.mode & 0o077) !== 0) {
    throw new Error("utility logger state directory is not private to this user");
  }
}
const loggerPidPath = runId ? `${loggerStateDir}/${runId}.json` : undefined;

function isExpectedLogger(pid, expectedRunId) {
  const arguments_ = fs.readFileSync(`/proc/${pid}/cmdline`, "utf8").split("\0");
  const logIndex = arguments_.indexOf("log");
  return (
    arguments_[0]?.endsWith("node") &&
    arguments_.includes("--input-type=module") &&
    arguments_.includes("-") &&
    logIndex >= 0 &&
    arguments_[logIndex + 2] === expectedRunId
  );
}

if (action === "stop-log") {
  try {
    const loggerPid = Number(JSON.parse(fs.readFileSync(loggerPidPath, "utf8")).pid);
    if (!Number.isSafeInteger(loggerPid) || loggerPid <= 1) {
      throw new Error("logger pid file was invalid");
    }
    if (!isExpectedLogger(loggerPid, runId)) {
      fs.rmSync(loggerPidPath, { force: true });
      console.log(JSON.stringify({ type: "utility_plug", event: "log_stale", run_id: runId }));
      process.exit(0);
    }
    process.kill(loggerPid, "SIGTERM");
    fs.rmSync(loggerPidPath, { force: true });
    console.log(JSON.stringify({ type: "utility_plug", event: "log_stopped", run_id: runId }));
  } catch (error) {
    if (error?.code !== "ENOENT" && error?.code !== "ESRCH") throw error;
    fs.rmSync(loggerPidPath, { force: true });
    console.log(JSON.stringify({ type: "utility_plug", event: "log_absent", run_id: runId }));
  }
  process.exit(0);
}

const config = JSON.parse(fs.readFileSync("/var/lib/homebridge/config.json", "utf8"));
const platform = config.platforms?.find(
  (candidate) => candidate.platform === "TplinkSmarthome",
);
if (!platform?.kasaUsername || !platform?.kasaPassword) {
  throw new Error("Homebridge Kasa credentials are unavailable");
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function report(device, event) {
  const realtime = device.emeter.realtime;
  console.log(
    JSON.stringify({
      type: "utility_plug",
      event,
      timestamp: new Date().toISOString(),
      on: device.relayState,
      volts: realtime.voltage ?? null,
      amps: realtime.current ?? null,
      watts: realtime.power ?? null,
    }),
  );
}

async function readAndReport(device, event) {
  await device.getSysInfo();
  if (device.supportsEmeter) await device.emeter.getRealtime();
  report(device, event);
}

async function connect() {
  // A logger can run for an hour. Periodic rediscovery replaces the live transport and used
  // to reset its in-flight HTTP request exactly one minute into a run, so this one-device
  // client performs only the initial discovery. Explicit reconnects below recover genuine
  // transient network/session failures.
  const discovery = new KlapDiscovery({
    credentials: { username: platform.kasaUsername, password: platform.kasaPassword },
    devices: [{ host: EXPECTED.host, port: 80 }],
    discoveryInterval: 86_400_000,
    timeout: 10_000,
  });

  try {
    const device = await new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("Utility Plug discovery timed out")),
        25_000,
      );
      discovery.on("device-new", (candidate) => {
        if (candidate.host !== EXPECTED.host) return;
        clearTimeout(timeout);
        resolve(candidate);
      });
      discovery.on("warning", (message) =>
        console.error(`utility-plug warning: ${message}`),
      );
      discovery.on("error", reject);
      discovery.start();
    });

    if (
      device.id !== EXPECTED.id ||
      device.alias !== EXPECTED.alias ||
      device.host !== EXPECTED.host
    ) {
      throw new Error(
        `refusing unexpected device ${device.alias} ${device.id} at ${device.host}`,
      );
    }
    return { device, discovery };
  } catch (error) {
    discovery.stop();
    throw error;
  }
}

let connection;
let ownsLoggerState = false;

async function withReconnect(operation) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await operation(connection.device);
    } catch (error) {
      if (attempt >= 3) throw error;
      console.error(
        `utility-plug transient failure, reconnecting (${attempt + 1}/3): ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
      connection.discovery.stop();
      await sleep(250 * 2 ** attempt);
      connection = await connect();
    }
  }
}

try {
  connection = await connect();
  if (action === "log") {
    fs.writeFileSync(loggerPidPath, JSON.stringify({ pid: process.pid }), {
      flag: "wx",
      mode: 0o600,
    });
    ownsLoggerState = true;
  }
  if (action === "on" || action === "off") {
    const desired = action === "on";
    await withReconnect(async (device) => {
      await device.setPowerState(desired);
      await readAndReport(device, action);
      if (device.relayState !== desired) throw new Error(`relay did not verify ${action}`);
    });
  } else if (action === "cycle") {
    await withReconnect(async (device) => {
      await device.setPowerState(false);
      // U6 is a persistent hardware safety lock. Its delayed-PGOOD preset must see a
      // genuine low-voltage power cycle; a one-second relay interruption empirically left
      // the lock asserted after a guarded high-speed run and made healthy startup look like
      // a no-motor fault. Five seconds provides explicit RC/discharge margin.
      await sleep(5_000);
      await device.setPowerState(true);
      await readAndReport(device, "cycle");
      if (!device.relayState) throw new Error("relay did not verify on after cycle");
    });
  } else if (action === "log") {
    let consecutiveOffSamples = 0;
    for (let sample = 0; sample < durationSeconds; sample += 1) {
      const relayState = await withReconnect(async (device) => {
        await readAndReport(device, "sample");
        return device.relayState;
      });
      if (!relayState) {
        consecutiveOffSamples += 1;
      } else {
        consecutiveOffSamples = 0;
      }
      if (consecutiveOffSamples >= 3) {
        throw new Error("Utility Plug remained off for three power samples");
      }
      if (sample + 1 < durationSeconds) await sleep(1_000);
    }
    report(connection.device, "summary");
  } else {
    await withReconnect((device) => readAndReport(device, "status"));
  }
} finally {
  connection?.discovery.stop();
  if (ownsLoggerState) fs.rmSync(loggerPidPath, { force: true });
}
