#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
candidate=${1:-}
profile=${2:-"$script_dir/52-loaded-acoustic-candidate.txt"}
if [ -z "$candidate" ]; then
    echo "usage: $0 <candidate> [profile]" >&2
    exit 2
fi
if [[ "$profile" != /* ]]; then
    profile="$PWD/$profile"
fi

validation=$(python3 "$script_dir/validate_loaded_profile.py" "$profile" \
    --mode candidate --candidate "$candidate")
echo "$validation"
if [ "${STILLAIR_DRY_RUN:-0}" = "1" ]; then
    exit 0
fi

export STILLAIR_CONFIG_MODE=verified
export STILLAIR_REQUIRE_CLEAN=1
export STILLAIR_TUNE_CANDIDATE=$candidate
export STILLAIR_REQUIRE_AUDIO=1
export STILLAIR_REQUIRE_SCOPE=1
export STILLAIR_AUDIO_DEVICE=${STILLAIR_AUDIO_DEVICE:-Razer Seiren V3 Mini}
export STILLAIR_SCOPE_RECIPE=${STILLAIR_SCOPE_RECIPE:-"$script_dir/scope-loaded-startup.json"}
exec bash "$script_dir/08-flash-and-unloaded-profile.sh" "$profile"
