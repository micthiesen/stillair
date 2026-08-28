#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
utility_plug="$script_dir/utility-plug.sh"
board_port=${STILLAIR_PORT:-}
timeout_seconds=${STILLAIR_MCF_CHECK_TIMEOUT:-20}
session_name="stillair-mcf-check-$$"
log_file="/tmp/stillair-mcf-presence-$$.log"
screen_config="/tmp/stillair-mcf-presence-$$.screenrc"
plug_on=0

# shellcheck disable=SC2329 # invoked indirectly by the traps below
cleanup() {
    status=$?
    trap - EXIT INT TERM
    screen -S "$session_name" -X quit >/dev/null 2>&1 || true
    if [ "$plug_on" -eq 1 ]; then
        if ! "$utility_plug" off >/dev/null; then
            echo "CRITICAL: Utility Plug could not be switched off" >&2
            status=3
        else
            echo "POWER: Utility Plug off"
        fi
    fi
    rm -f "$log_file" "$screen_config"
    exit "$status"
}
trap cleanup EXIT INT TERM

command -v screen >/dev/null || {
    echo "screen is required for the persistent boot-log check" >&2
    exit 2
}

discover_board_port() {
    discovered=()
    for candidate in /dev/cu.usbmodem*; do
        [ -e "$candidate" ] || continue
        discovered+=("$candidate")
    done
    if [ "${#discovered[@]}" -gt 1 ]; then
        echo "FAIL: multiple board ports found; set STILLAIR_PORT explicitly" >&2
        return 2
    fi
    if [ "${#discovered[@]}" -eq 1 ]; then
        board_port=${discovered[0]}
        return 0
    fi
    return 1
}

board_port_present() {
    if [ -n "$board_port" ]; then
        [ -e "$board_port" ]
    else
        discover_board_port >/dev/null 2>&1
    fi
}

deadline=$((SECONDS + timeout_seconds))
"$utility_plug" off >/dev/null
while board_port_present; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        echo "FAIL: board port remained after power-off: ${board_port:-auto-detected}" >&2
        exit 2
    fi
    sleep 0.1
done

"$utility_plug" on >/dev/null
plug_on=1
deadline=$((SECONDS + timeout_seconds))
while ! board_port_present; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        echo "FAIL: no Espressif board port appeared" >&2
        exit 2
    fi
    sleep 0.1
done
if [ -z "$board_port" ]; then
    discover_board_port
fi

# Keep one serial connection open through the entire boot. Reopening the port for separate
# CLI commands resets the ESP and can make a queued `fault clear` look more useful than it was.
# macOS ships an older screen without `-Logfile`, so supply the unique path through screenrc.
printf 'logfile %s\nlogfile flush 0\ndeflog on\n' "$log_file" >"$screen_config"
screen -c "$screen_config" -dmS "$session_name" "$board_port" 115200

while [ "$SECONDS" -lt "$deadline" ]; do
    if [ -f "$log_file" ]; then
        if grep -q "MCF8316D found at I2C target" "$log_file"; then
            target=$(sed -n 's/.*MCF8316D found at I2C target \(0x[[:xdigit:]]*\).*/\1/p' "$log_file" | tail -1)
            echo "PASS: MCF8316D acknowledged at I2C target ${target:-unknown}"
            exit 0
        fi
        if grep -q "no MCF8316D on the I2C bus" "$log_file"; then
            echo "FAIL: MCF8316D did not acknowledge after wake and address scan" >&2
            exit 1
        fi
    fi
    sleep 0.1
done

echo "FAIL: boot log did not produce an MCF presence result within ${timeout_seconds}s" >&2
exit 2
