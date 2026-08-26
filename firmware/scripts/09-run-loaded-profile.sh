#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
profile=${1:-"$script_dir/51-loaded-golden-baseline.txt"}
if [[ "$profile" != /* ]]; then
    profile="$PWD/$profile"
fi

validation=$(python3 "$script_dir/validate_loaded_profile.py" "$profile" --mode verified)
echo "$validation"
if [ "${STILLAIR_DRY_RUN:-0}" = "1" ]; then
    exit 0
fi

export STILLAIR_CONFIG_MODE=verified
export STILLAIR_REQUIRE_AUDIO=1
export STILLAIR_REQUIRE_SCOPE=1
export STILLAIR_AUDIO_DEVICE=${STILLAIR_AUDIO_DEVICE:-Razer Seiren V3 Mini}
export STILLAIR_SCOPE_RECIPE=${STILLAIR_SCOPE_RECIPE:-"$script_dir/scope-loaded-startup.json"}
exec bash "$script_dir/08-flash-and-unloaded-profile.sh" "$profile"
