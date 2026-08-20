#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
firmware_dir=$(cd -- "$script_dir/.." && pwd)
repo_dir=$(cd -- "$firmware_dir/.." && pwd)
board_port=${STILLAIR_PORT:-}
board_port_explicit=0
if [ -n "$board_port" ]; then
    board_port_explicit=1
fi
skip_flash=${STILLAIR_SKIP_FLASH:-0}
power_log_seconds=${STILLAIR_RUN_SECONDS:-}
camera_url=${STILLAIR_CAMERA_URL:-}
camera_center=${STILLAIR_CAMERA_CENTER:-704,355}
camera_radius=${STILLAIR_CAMERA_RADIUS:-110,205}
# Track only the rigid inner arm. The outer magnet/tape stick visibly flexes above 140 RPM
# and made a healthy shaft look as if it were hunting; edge-timestamped Hall periods proved
# that the rotor itself remained smooth through those apparent excursions.
camera_stick_radius=${STILLAIR_CAMERA_STICK_RADIUS:-0,100}
camera_method=${STILLAIR_CAMERA_METHOD:-stick}
camera_forward_sign=${STILLAIR_CAMERA_FORWARD_SIGN:-1}
run_id=$(date +%Y%m%d-%H%M%S)
motor_log="/tmp/stillair-${run_id}-motor.log"
power_log="/tmp/stillair-${run_id}-power.log"
camera_video="/tmp/stillair-${run_id}-rotor.mp4"
camera_csv="/tmp/stillair-${run_id}-rotor.csv"
camera_log="/tmp/stillair-${run_id}-camera.log"
camera_progress="/tmp/stillair-${run_id}-camera.progress"
camera_segment_dir="/tmp/stillair-${run_id}-camera-segments"
camera_concat="/tmp/stillair-${run_id}-camera.concat"
camera_guard_log="/tmp/stillair-${run_id}-camera-guard.log"
camera_guard_stop="/tmp/stillair-${run_id}-camera-guard.stop"
camera_decelerating="/tmp/stillair-${run_id}-camera-decelerating"
plateau_log="/tmp/stillair-${run_id}-plateaus.log"
power_plateau_log="/tmp/stillair-${run_id}-power-plateaus.log"
tach_plateau_log="/tmp/stillair-${run_id}-tach-plateaus.log"
fault_diagnostics_log="/tmp/stillair-${run_id}-fault-diagnostics.log"
utility_plug="$script_dir/utility-plug.sh"
stillair="$firmware_dir/target/debug/stillair"
image="$firmware_dir/app/target/riscv32imac-unknown-none-elf/debug/stillair"
profile=${1:-"$script_dir/18-unloaded-startup-camera.txt"}
if [[ "$profile" != /* ]]; then
    profile="$PWD/$profile"
fi
if [ -z "$power_log_seconds" ]; then
    # Sum every declared worst-case wait/dwell and leave a minute for setup and command ACKs.
    # Evidence children are stopped when the motor profile finishes, so this is a ceiling, not
    # an amount of idle time added to successful runs.
    power_log_seconds=$(awk '
        $1 == "dwell" { total += $2 }
        $1 == "wait" {
            for (i = 1; i <= NF; i++) if ($i == "--for") total += $(i + 1)
        }
        END { print int(total + 60) }
    ' "$profile")
fi
power_is_on=1
power_pid=
camera_pid=
camera_guard_pid=
camera_guard_failed=0
motor_pid=

discover_board_port() {
    discovered_ports=()
    discovered_callout_ports=()
    while IFS= read -r candidate; do
        if [ -n "$candidate" ]; then
            discovered_ports+=("$candidate")
            if [[ "$candidate" == /dev/cu.* ]]; then
                discovered_callout_ports+=("$candidate")
            fi
        fi
    done < <(espflash list-ports --name-only --skip-update-check)
    if [ "${#discovered_callout_ports[@]}" -gt 0 ]; then
        discovered_ports=("${discovered_callout_ports[@]}")
    fi
    if [ "${#discovered_ports[@]}" -gt 1 ]; then
        echo "multiple Espressif board ports found; set STILLAIR_PORT explicitly" >&2
        return 2
    fi
    if [ "${#discovered_ports[@]}" -eq 1 ]; then
        board_port=${discovered_ports[0]}
        return 0
    fi
    return 1
}

wait_for_board_port() {
    if [ "$board_port_explicit" -eq 1 ]; then
        for _ in $(seq 1 100); do
            [ -e "$board_port" ] && return 0
            sleep 0.1
        done
        return 1
    fi
    board_port=
    for _ in $(seq 1 50); do
        discovery_status=0
        discover_board_port || discovery_status=$?
        [ "$discovery_status" -eq 0 ] && return 0
        [ "$discovery_status" -eq 2 ] && return 2
        sleep 0.1
    done
    return 1
}

job_running() {
    jobs -pr | grep -qx "$1"
}

finish_camera() {
    if [ -n "$camera_pid" ]; then
        kill -TERM "$camera_pid" >/dev/null 2>&1 || true
        wait "$camera_pid" >/dev/null 2>&1 || true
        camera_pid=
    fi
    if [ -n "$camera_guard_pid" ]; then
        : >"$camera_guard_stop"
        if ! wait "$camera_guard_pid" >/dev/null 2>&1; then
            camera_guard_failed=1
        fi
        camera_guard_pid=
    fi
    if [ -d "$camera_segment_dir" ]; then
        : >"$camera_concat"
        for segment in "$camera_segment_dir"/*.mp4; do
            [ -e "$segment" ] || continue
            printf "file '%s'\n" "$segment" >>"$camera_concat"
        done
        if [ -s "$camera_concat" ]; then
            ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 \
                -i "$camera_concat" -c copy "$camera_video" >/dev/null 2>&1 || true
        fi
    fi
}

stop_power_logger() {
    if [ -n "$power_pid" ]; then
        stop_log_status=0
        if ! "$utility_plug" stop-log "$run_id" >/dev/null 2>&1; then
            echo "remote Utility Plug logger stop could not be confirmed" >&2
            stop_log_status=1
        fi
        kill "$power_pid" >/dev/null 2>&1 || true
        wait "$power_pid" >/dev/null 2>&1 || true
        power_pid=
        return "$stop_log_status"
    fi
    return 0
}

ensure_power_off() {
    for _ in 1 2 3; do
        if "$utility_plug" off >"/tmp/stillair-${run_id}-off-status.log" 2>&1 &&
            grep -q '"on":false' "/tmp/stillair-${run_id}-off-status.log"; then
            power_is_on=0
            return 0
        fi
    done
    echo "CRITICAL: Utility Plug off could not be verified; use the physical cutoff" >&2
    return 1
}

fail_safe() {
    status=$?
    trap - EXIT INT TERM
    # The long-running script owns the serial port. Release it before attempting an
    # independent disarm; reversing these steps leaves the motor command active because the
    # second client cannot open the port.
    if [ -n "$motor_pid" ]; then
        kill "$motor_pid" >/dev/null 2>&1 || true
        wait "$motor_pid" >/dev/null 2>&1 || true
        motor_pid=
    fi
    if [ "$status" -ne 0 ]; then
        if [ -n "$board_port" ] && [ -e "$board_port" ]; then
            # Preserve the volatile MCF evidence before disarm or relay-off can erase it.
            # This is read-only and best-effort; the independently verified power cutoff
            # remains authoritative if the console or I2C bus is itself unhealthy.
            "$stillair" --port "$board_port" script \
                "$script_dir/28-post-run-diagnostics.txt" \
                >"$fault_diagnostics_log" 2>&1 || true
            "$stillair" --port "$board_port" disarm >/dev/null 2>&1 || true
        fi
    fi
    stop_power_logger || true
    if [ "$status" -ne 0 ] && [ "$power_is_on" -eq 1 ]; then
        ensure_power_off || true
    fi
    finish_camera
    rm -f "$camera_progress" "$camera_guard_stop" "$camera_decelerating" \
        "$camera_decelerating.command" "$camera_concat"
    if [ "$status" -ne 0 ]; then
        if [ "$power_is_on" -eq 0 ]; then
            echo "profile failed; Utility Plug was switched off and verified" >&2
        else
            echo "profile failed; disarm was attempted, use the monitored physical cutoff" >&2
        fi
    fi
    exit "$status"
}
trap fail_safe EXIT INT TERM

cd "$firmware_dir"
cargo build -p stillair-cli --bins
if [ "$power_log_seconds" -gt 3600 ]; then
    echo "STILLAIR_RUN_SECONDS must be at most 3600" >&2
    exit 1
fi
if [ -z "$camera_url" ]; then
    echo "autonomous runs require STILLAIR_CAMERA_URL for physical monitoring" >&2
    exit 1
fi
case "$camera_url" in
    rtsps://*) ;;
    *) echo "STILLAIR_CAMERA_URL must use rtsps://" >&2; exit 1 ;;
esac
case "$camera_url" in
    *"'"* | *\\* | *$'\n'* | *$'\r'*)
        echo "STILLAIR_CAMERA_URL contains characters unsafe for the private ffconcat descriptor" >&2
        exit 1
        ;;
esac
"$utility_plug" on
if [ "$skip_flash" -eq 0 ]; then
    cd "$firmware_dir/app"
    cargo build

    # The ESP dev board is powered from the controller rail. Restore the rail and wait for USB
    # before flashing, then cycle the whole fan supply and restage the volatile MCF image.
    if ! wait_for_board_port; then
        echo "board port did not appear after enabling Utility Plug" >&2
        exit 1
    fi
    cd "$repo_dir"
    espflash flash --port "$board_port" --non-interactive "$image"
    "$utility_plug" cycle
    if [ "$board_port_explicit" -eq 0 ]; then
        board_port=
    fi
    if ! wait_for_board_port; then
        echo "board port did not return after flash/power cycle" >&2
        exit 1
    fi
fi
if [ -z "$board_port" ] || [ ! -e "$board_port" ]; then
    if ! wait_for_board_port; then
        echo "Espressif board port is unavailable" >&2
        exit 1
    fi
fi
board_ready=0
for _ in $(seq 1 100); do
    if "$stillair" --port "$board_port" state >/dev/null 2>&1; then
        board_ready=1
        break
    fi
    sleep 0.1
done
if [ "$board_ready" -ne 1 ]; then
    echo "board console did not become responsive" >&2
    exit 1
fi
# The MCF image is volatile and is erased by every fan-supply power cycle. Re-stage it even
# when the ESP firmware itself is current and flashing is skipped; readback makes this safe
# and idempotent when the image happened to survive.
"$stillair" --port "$board_port" config stage

# Supply logging and MCF tracking run concurrently on their separate USB ports.
if [ -n "$camera_url" ]; then
    # Feed the credential-bearing RTSP URL through a private descriptor, not argv or logs.
    exec 3<<<"ffconcat version 1.0
file '$camera_url'
option rtsp_transport tcp"
    mkdir "$camera_segment_dir"
    rm -f "$camera_guard_stop" "$camera_decelerating"
    ffmpeg -hide_banner -loglevel error -nostats -y -stats_period 0.1 \
        -progress "$camera_progress" -f concat -safe 0 \
        -protocol_whitelist file,pipe,tcp,tls,udp,rtp,srtp,rtsp,crypto \
        -i pipe:3 \
        -map 0:v:0 -map '0:a:0?' -t "$power_log_seconds" \
        -c:v libx264 -preset ultrafast -crf 18 -c:a aac -b:a 128k \
        -g 150 -keyint_min 150 -sc_threshold 0 \
        -f segment -segment_time 5 -segment_time_delta 0.1 -reset_timestamps 1 \
        "$camera_segment_dir/%05d.mp4" >"$camera_log" 2>&1 &
    camera_pid=$!
    exec 3<&-
    uv run "$script_dir/guard_rotor_segments.py" "$camera_segment_dir" \
        --stop-file "$camera_guard_stop" --decelerating-file "$camera_decelerating" \
        --center "$camera_center" \
        --radius "$camera_stick_radius" >"$camera_guard_log" 2>&1 &
    camera_guard_pid=$!
    camera_offset_us=
    for _ in $(seq 1 100); do
        if ! job_running "$camera_pid"; then
            echo "camera capture exited before its first frame" >&2
            exit 1
        fi
        camera_offset_us=$(awk -F= '$1 == "out_time_us" && $2 ~ /^[0-9]+$/ { value=$2 } END { if (value > 0) print value }' "$camera_progress" 2>/dev/null || true)
        [ -n "$camera_offset_us" ] && break
        sleep 0.1
    done
    if [ -z "$camera_offset_us" ]; then
        echo "camera capture produced no synchronization timestamp" >&2
        exit 1
    fi
fi
"$utility_plug" log --for "$power_log_seconds" --id "$run_id" >"$power_log" 2>&1 &
power_pid=$!
for _ in $(seq 1 100); do
    if ! job_running "$power_pid"; then
        echo "Utility Plug power evidence failed before its first sample" >&2
        exit 1
    fi
    grep -q '"on":true' "$power_log" 2>/dev/null && break
    sleep 0.1
done
if ! grep -q '"on":true' "$power_log" 2>/dev/null; then
    echo "Utility Plug power evidence did not confirm the relay on" >&2
    exit 1
fi
if [ -n "$camera_pid" ]; then
    latest_camera_offset_us=$(awk -F= '$1 == "out_time_us" && $2 ~ /^[0-9]+$/ { value=$2 } END { if (value > 0) print value }' "$camera_progress")
    if [ -n "$latest_camera_offset_us" ]; then
        camera_offset_us=$latest_camera_offset_us
    fi
fi
# Anchor the CLI's relative `# t=` timestamps to the Utility Plug's ISO timestamps. One-second
# wall-clock resolution is sufficient because power plateaus discard their first two seconds.
date -u '+# wall_start=%Y-%m-%dT%H:%M:%SZ' >"$motor_log"
"$stillair" --port "$board_port" script "$profile" >>"$motor_log" 2>&1 &
motor_pid=$!
elapsed_tenths=0
deadline_tenths=$((power_log_seconds * 10))
while job_running "$motor_pid" && [ "$elapsed_tenths" -lt "$deadline_tenths" ]; do
    # Follow the latest motion command, not the existence of any earlier stop. Multi-start
    # profiles otherwise leave the camera in deceleration mode for every subsequent run.
    awk '/^# t=[0-9.]+s (run|pct|stop)( |$)/ { command=$3 } END { print command }' \
        "$motor_log" >"$camera_decelerating.command" 2>/dev/null || true
    if grep -qx 'stop' "$camera_decelerating.command" 2>/dev/null; then
        : >"$camera_decelerating"
    else
        rm -f "$camera_decelerating"
    fi
    if [ -n "$camera_pid" ] && ! job_running "$camera_pid"; then
        echo "camera evidence capture stopped while the motor profile was running" >&2
        exit 1
    fi
    if [ -n "$camera_guard_pid" ] && ! job_running "$camera_guard_pid"; then
        echo "live physical-motion guard rejected the run" >&2
        tail -5 "$camera_guard_log" >&2 || true
        exit 1
    fi
    if [ -n "$power_pid" ] && ! job_running "$power_pid"; then
        echo "Utility Plug power evidence stopped while the motor profile was running" >&2
        exit 1
    fi
    sleep 0.1
    elapsed_tenths=$((elapsed_tenths + 1))
done
if job_running "$motor_pid"; then
    echo "motor profile exceeded ${power_log_seconds}s wall-clock deadline" >&2
    kill "$motor_pid" >/dev/null 2>&1 || true
fi
if ! wait "$motor_pid"; then
    motor_pid=
    exit 1
fi
motor_pid=
stop_power_logger
if [ -n "$camera_pid" ]; then
    finish_camera
    if [ "$camera_guard_failed" -ne 0 ]; then
        echo "live physical-motion guard rejected the run" >&2
        tail -5 "$camera_guard_log" >&2 || true
        exit 1
    fi
    if grep -qE '^[[:space:]]*(run|pct)[[:space:]]' "$profile"; then
        uv run "$script_dir/analyze_rotor_video.py" "$camera_video" \
            --center "$camera_center" --radius "$camera_radius" \
            --stick-radius "$camera_stick_radius" --method "$camera_method" \
            --profile --csv "$camera_csv" \
            >"$camera_log.summary"
    fi
    if [ -s "$camera_csv" ] && grep -qE '^# t=[0-9.]+s dwell ' "$motor_log"; then
        uv run "$script_dir/analyze_profile_plateaus.py" "$motor_log" "$camera_csv" \
            --camera-offset-us "$camera_offset_us" --forward-sign "$camera_forward_sign" \
            >"$plateau_log"
    fi
fi
if grep -qE '^# t=[0-9.]+s dwell ' "$motor_log"; then
    python3 "$script_dir/analyze_profile_power.py" "$motor_log" "$power_log" \
        >"$power_plateau_log"
fi
if grep -qE '^# t=[0-9.]+s stream [0-9]+ --for [0-9]+' "$motor_log"; then
    python3 "$script_dir/analyze_tach_streams.py" "$motor_log" >"$tach_plateau_log"
fi
rm -f "$camera_progress" "$camera_guard_stop" "$camera_decelerating" \
    "$camera_decelerating.command" "$camera_concat"

# Both tools verified their own stop and health conditions. Leave bench power available.
trap - EXIT INT TERM
echo "motor_log=$motor_log"
echo "power_log=$power_log"
if [ -n "$camera_url" ]; then
    echo "camera_video=$camera_video"
    echo "camera_csv=$camera_csv"
    echo "camera_guard_log=$camera_guard_log"
fi
grep '"type":".*_summary"' "$motor_log" || true
tail -1 "$power_log"
if [ -s "$power_plateau_log" ]; then
    cat "$power_plateau_log"
fi
if [ -s "$tach_plateau_log" ]; then
    cat "$tach_plateau_log"
fi
if [ -n "$camera_url" ]; then
    cat "$camera_guard_log"
    if [ -s "$camera_log.summary" ]; then
        cat "$camera_log.summary"
    fi
    if [ -s "$plateau_log" ]; then
        cat "$plateau_log"
    fi
fi
