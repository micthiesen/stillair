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
config_mode=${STILLAIR_CONFIG_MODE:-stage}
tune_candidate=${STILLAIR_TUNE_CANDIDATE:-}
require_clean=${STILLAIR_REQUIRE_CLEAN:-0}
power_log_seconds=${STILLAIR_RUN_SECONDS:-}
camera_url=${STILLAIR_CAMERA_URL:-}
camera_url_file=${STILLAIR_CAMERA_URL_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/stillair/camera-url}
if [ -z "$camera_url" ] && [ -r "$camera_url_file" ]; then
    IFS= read -r camera_url <"$camera_url_file"
fi
audio_device=${STILLAIR_AUDIO_DEVICE:-}
require_audio=${STILLAIR_REQUIRE_AUDIO:-0}
scope_recipe=${STILLAIR_SCOPE_RECIPE:-}
require_scope=${STILLAIR_REQUIRE_SCOPE:-0}
scope_simulate=${STILLAIR_SCOPE_SIMULATE:-0}
camera_center=${STILLAIR_CAMERA_CENTER:-704,355}
camera_radius=${STILLAIR_CAMERA_RADIUS:-110,205}
# Track only the rigid inner arm. The outer magnet/tape stick visibly flexes above 140 RPM
# and made a healthy shaft look as if it were hunting; edge-timestamped Hall periods proved
# that the rotor itself remained smooth through those apparent excursions.
camera_stick_radius=${STILLAIR_CAMERA_STICK_RADIUS:-0,100}
camera_method=${STILLAIR_CAMERA_METHOD:-stick}
camera_forward_sign=${STILLAIR_CAMERA_FORWARD_SIGN:-1}
run_id=$(date +%Y%m%d-%H%M%S)
run_git_commit=$(git -C "$repo_dir" rev-parse HEAD)
if [ "$require_clean" = "1" ] && [ -n "$(git -C "$repo_dir" status --porcelain)" ]; then
    echo "loaded evidence requires a clean worktree so the manifest identifies the binary" >&2
    exit 1
fi
evidence_root=${STILLAIR_EVIDENCE_ROOT:-/tmp}
run_dir="$evidence_root/stillair-$run_id"
mkdir -p "$evidence_root"
mkdir "$run_dir"
motor_log="$run_dir/motor.log"
power_log="$run_dir/power.log"
camera_video="$run_dir/rotor.mp4"
camera_csv="$run_dir/rotor.csv"
camera_log="$run_dir/camera.log"
camera_progress="$run_dir/camera.progress"
camera_segment_dir="$run_dir/camera-segments"
camera_concat="$run_dir/camera.concat"
camera_guard_log="$run_dir/camera-guard.log"
camera_guard_stop="$run_dir/camera-guard.stop"
camera_decelerating="$run_dir/camera-decelerating"
plateau_log="$run_dir/plateaus.json"
power_plateau_log="$run_dir/power-plateaus.json"
tach_plateau_log="$run_dir/tach-plateaus.jsonl"
fault_diagnostics_log="$run_dir/fault-diagnostics.log"
candidate_log="$run_dir/candidate.log"
audio_file="$run_dir/microphone.wav"
audio_log="$run_dir/microphone.log"
audio_summary="$run_dir/audio-windows.jsonl"
scope_dir="$run_dir/scope"
scope_log="$run_dir/scope.log"
scope_ready="$run_dir/scope.ready"
run_manifest="$run_dir/manifest.json"
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
        $1 == "stream" && $2 ~ /^[0-9]+$/ {
            for (i = 1; i <= NF; i++) if ($i == "--for") total += $(i + 1)
        }
        ($1 == "speed" || $1 == "estimator") && $2 == "sample" {
            duration = 10
            for (i = 1; i <= NF; i++) if ($i == "--for") duration = $(i + 1)
            total += duration
        }
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
audio_pid=
scope_pid=
audio_start_ns=
motor_start_ns=
candidate_applied_ns=

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

finish_audio() {
    if [ -n "$audio_pid" ]; then
        kill -INT "$audio_pid" >/dev/null 2>&1 || true
        wait "$audio_pid" >/dev/null 2>&1 || true
        audio_pid=
    fi
}

finish_scope() {
    if [ -n "$scope_pid" ]; then
        kill -TERM "$scope_pid" >/dev/null 2>&1 || true
        wait "$scope_pid" >/dev/null 2>&1 || true
        scope_pid=
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
        if "$utility_plug" off >"$run_dir/off-status.log" 2>&1 &&
            grep -q '"on":false' "$run_dir/off-status.log"; then
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
    finish_audio
    finish_scope
    finish_camera
    rm -f "$camera_progress" "$camera_guard_stop" "$camera_decelerating" \
        "$camera_decelerating.command" "$camera_concat" "$scope_ready"
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
case "$config_mode" in
    stage | verified) ;;
    *) echo "STILLAIR_CONFIG_MODE must be stage or verified" >&2; exit 1 ;;
esac
if [ -n "$tune_candidate" ] && [ "$config_mode" != "verified" ]; then
    echo "loaded tuning candidates require STILLAIR_CONFIG_MODE=verified" >&2
    exit 1
fi
if [ "$require_audio" = "1" ] && [ -z "$audio_device" ]; then
    echo "loaded runs require STILLAIR_AUDIO_DEVICE for the fixed dedicated microphone" >&2
    exit 1
fi
if [ "$require_scope" = "1" ] && [ -z "$scope_recipe" ]; then
    echo "loaded runs require STILLAIR_SCOPE_RECIPE" >&2
    exit 1
fi
if [ -n "$scope_recipe" ] && [ ! -f "$scope_recipe" ]; then
    echo "scope recipe does not exist: $scope_recipe" >&2
    exit 1
fi
if [ -n "$scope_recipe" ] && [ "$scope_simulate" != "1" ] && \
    [ "${STILLAIR_SCOPE_ISOLATED_CONFIRMED:-0}" != "1" ]; then
    echo "set STILLAIR_SCOPE_ISOLATED_CONFIRMED=1 after physically confirming VDS1022I" >&2
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
if [ "$config_mode" = "stage" ]; then
    # Unloaded commissioning uses the reviewed volatile image after every motor-power cycle.
    "$stillair" --port "$board_port" config stage
else
    # Loaded capture must begin from the persistent golden image exactly as booted. A later
    # candidate operation may derive one volatile field from this proven base, but a failed
    # check is never turned into a staged substitute.
    config_check=$("$stillair" --port "$board_port" config check)
    echo "$config_check"
    if ! grep -q '"config":"verified"' <<<"$config_check"; then
        echo "loaded reference requires config=verified; refusing to stage a substitute" >&2
        exit 1
    fi
fi

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
if [ -n "$audio_device" ]; then
    audio_start_ns=$(python3 -c 'import time; print(time.time_ns())')
    ffmpeg -hide_banner -loglevel error -nostats -y \
        -thread_queue_size 512 -f avfoundation -i ":$audio_device" \
        -map 0:a:0 -ac 1 -ar 96000 -c:a pcm_s24le "$audio_file" \
        >"$audio_log" 2>&1 &
    audio_pid=$!
    for _ in $(seq 1 100); do
        if ! job_running "$audio_pid"; then
            echo "dedicated microphone capture exited before producing audio" >&2
            tail -10 "$audio_log" >&2 || true
            exit 1
        fi
        [ -s "$audio_file" ] && break
        sleep 0.1
    done
    if [ ! -s "$audio_file" ]; then
        echo "dedicated microphone produced no WAV header" >&2
        exit 1
    fi
fi
if [ -n "$scope_recipe" ]; then
    scope_args=()
    if [ "$scope_simulate" = "1" ]; then
        scope_args+=(--simulate)
    fi
    rm -f "$scope_ready"
    uv run "$script_dir/capture_owon_scope.py" \
        --recipe "$scope_recipe" --output "$scope_dir" \
        --seconds "$power_log_seconds" --ready-file "$scope_ready" \
        "${scope_args[@]}" >"$scope_log" 2>&1 &
    scope_pid=$!
    for _ in $(seq 1 300); do
        if ! job_running "$scope_pid"; then
            echo "scope capture exited before its first verified frame" >&2
            tail -20 "$scope_log" >&2 || true
            exit 1
        fi
        [ -s "$scope_ready" ] && break
        sleep 0.1
    done
    if [ ! -s "$scope_ready" ]; then
        echo "scope capture produced no verified frame within 30 seconds" >&2
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
if [ -n "$tune_candidate" ]; then
    candidate_applied_ns=$(python3 -c 'import time; print(time.time_ns())')
    "$stillair" --port "$board_port" config tune "$tune_candidate" >"$candidate_log"
    if ! grep -q '"config":"tuning"' "$candidate_log"; then
        echo "loaded candidate did not produce a verified tuning image" >&2
        cat "$candidate_log" >&2
        exit 1
    fi
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
motor_start_ns=$(python3 -c 'import time; print(time.time_ns())')
echo "# wall_start_ns=$motor_start_ns" >>"$motor_log"
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
    if [ -n "$audio_pid" ] && ! job_running "$audio_pid"; then
        echo "dedicated microphone capture stopped while the motor profile was running" >&2
        tail -10 "$audio_log" >&2 || true
        exit 1
    fi
    if [ -n "$scope_pid" ] && ! job_running "$scope_pid"; then
        echo "scope evidence capture stopped while the motor profile was running" >&2
        tail -20 "$scope_log" >&2 || true
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
if [ -n "$audio_pid" ]; then
    finish_audio
    audio_probe=$(ffprobe -v error -select_streams a:0 \
        -show_entries stream=sample_rate,channels,bits_per_sample \
        -of default=noprint_wrappers=1 "$audio_file")
    if ! grep -q '^sample_rate=96000$' <<<"$audio_probe" || \
        ! grep -q '^channels=1$' <<<"$audio_probe" || \
        ! grep -q '^bits_per_sample=24$' <<<"$audio_probe"; then
        echo "dedicated microphone WAV is not mono 24-bit/96 kHz" >&2
        echo "$audio_probe" >&2
        exit 1
    fi
    uv run "$script_dir/analyze_profile_audio.py" "$motor_log" "$audio_file" \
        --audio-start-ns "$audio_start_ns" --motor-start-ns "$motor_start_ns" \
        >"$audio_summary"
fi
if [ -n "$scope_pid" ]; then
    finish_scope
    if [ ! -s "$scope_dir/summary.json" ]; then
        echo "scope capture did not finish with a summary" >&2
        tail -20 "$scope_log" >&2 || true
        exit 1
    fi
fi
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
    "$camera_decelerating.command" "$camera_concat" "$scope_ready"

git_commit=$(git -C "$repo_dir" rev-parse HEAD)
if [ "$require_clean" = "1" ] && {
    [ "$git_commit" != "$run_git_commit" ] ||
        [ -n "$(git -C "$repo_dir" status --porcelain)" ]
}; then
    echo "repository changed during loaded evidence capture; refusing the manifest" >&2
    exit 1
fi
manifest_args=(
    --field "run_id=$run_id"
    --field "git_commit=$run_git_commit"
    --field "config_mode=$config_mode"
    --field "motor_start_ns=$motor_start_ns"
    --artifact "profile=$profile"
    --artifact "motor_log=$motor_log"
    --artifact "power_log=$power_log"
)
if [ -n "$tune_candidate" ]; then
    manifest_args+=(
        --field "tune_candidate=$tune_candidate"
        --field "candidate_applied_ns=$candidate_applied_ns"
        --artifact "candidate_log=$candidate_log"
    )
fi
if [ -n "$camera_url" ]; then
    manifest_args+=(--artifact "camera_video=$camera_video" --artifact "camera_csv=$camera_csv")
fi
if [ -n "$audio_device" ]; then
    manifest_args+=(
        --field "audio_start_ns=$audio_start_ns"
        --artifact "microphone_wav=$audio_file"
        --artifact "audio_summary=$audio_summary"
    )
fi
if [ -n "$scope_recipe" ]; then
    manifest_args+=(--artifact "scope_recipe=$scope_recipe" --artifact "scope_capture=$scope_dir")
fi
python3 "$script_dir/write_evidence_manifest.py" "$run_manifest" "${manifest_args[@]}"

# Both tools verified their own stop and health conditions. Leave bench power available.
trap - EXIT INT TERM
echo "run_dir=$run_dir"
echo "manifest=$run_manifest"
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
if [ -n "$audio_device" ]; then
    echo "microphone_wav=$audio_file"
    cat "$audio_summary"
fi
if [ -n "$scope_recipe" ]; then
    echo "scope_capture=$scope_dir"
    cat "$scope_dir/summary.json"
fi
