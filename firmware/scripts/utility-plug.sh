#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
action=${1:-status}

case "$action" in
    status | on | off | cycle)
        [ "$#" -eq 1 ] || { echo "usage: $0 status|on|off|cycle" >&2; exit 2; }
        ;;
    log)
        [ "$#" -eq 5 ] && [ "$2" = "--for" ] && [ "$4" = "--id" ] || {
            echo "usage: $0 log --for SECONDS --id YYYYMMDD-HHMMSS" >&2
            exit 2
        }
        case "$3" in
            '' | *[!0-9]*) echo "SECONDS must be an integer" >&2; exit 2 ;;
        esac
        case "$5" in
            ????????-??????) ;;
            *) echo "run id must be YYYYMMDD-HHMMSS" >&2; exit 2 ;;
        esac
        ;;
    stop-log)
        [ "$#" -eq 2 ] || { echo "usage: $0 stop-log YYYYMMDD-HHMMSS" >&2; exit 2; }
        case "$2" in
            ????????-??????) ;;
            *) echo "run id must be YYYYMMDD-HHMMSS" >&2; exit 2 ;;
        esac
        ;;
    *)
        echo "usage: $0 status|on|off|cycle|log --for SECONDS --id RUN_ID|stop-log RUN_ID" >&2
        exit 2
        ;;
esac

ssh_args=(
    -o BatchMode=yes
    -o ConnectTimeout=5
    -o HostKeyAlias=10.10.1.100
    homebridge.boris
)

if [ "$action" = "log" ]; then
    ssh "${ssh_args[@]}" docker exec -i homebridge node --input-type=module - log "$3" "$5" \
        <"$script_dir/utility_plug_controller.mjs"
elif [ "$action" = "stop-log" ]; then
    ssh "${ssh_args[@]}" docker exec -i homebridge node --input-type=module - stop-log 0 "$2" \
        <"$script_dir/utility_plug_controller.mjs"
else
    ssh "${ssh_args[@]}" docker exec -i homebridge node --input-type=module - "$action" \
        <"$script_dir/utility_plug_controller.mjs"
fi
