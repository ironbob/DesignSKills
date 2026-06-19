#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <adb-serial> <output-json>" >&2
  exit 2
fi

serial="$1"
output="$2"
mkdir -p "$(dirname "$output")"

adb_cmd=(adb -s "$serial")

manufacturer="$("${adb_cmd[@]}" shell getprop ro.product.manufacturer | tr -d '\r')"
model="$("${adb_cmd[@]}" shell getprop ro.product.model | tr -d '\r')"
android_version="$("${adb_cmd[@]}" shell getprop ro.build.version.release | tr -d '\r')"
api_level="$("${adb_cmd[@]}" shell getprop ro.build.version.sdk | tr -d '\r')"
wm_size="$("${adb_cmd[@]}" shell wm size 2>/dev/null | tr -d '\r' || true)"
wm_density="$("${adb_cmd[@]}" shell wm density 2>/dev/null | tr -d '\r' || true)"
network="$("${adb_cmd[@]}" shell dumpsys connectivity 2>/dev/null | grep -E 'NetworkAgentInfo|Active default network|mNetworkInfo' | head -20 | tr '\n' ';' || true)"

PROFILE_OUTPUT="$output" \
PROFILE_SERIAL="$serial" \
PROFILE_MANUFACTURER="$manufacturer" \
PROFILE_MODEL="$model" \
PROFILE_ANDROID_VERSION="$android_version" \
PROFILE_API_LEVEL="$api_level" \
PROFILE_SCREEN_SIZE="$wm_size" \
PROFILE_SCREEN_DENSITY="$wm_density" \
PROFILE_NETWORK="$network" \
python3 - <<'PY'
import json
import os
import pathlib

output = pathlib.Path(os.environ["PROFILE_OUTPUT"])
profile = {
    "adb_serial": os.environ["PROFILE_SERIAL"],
    "manufacturer": os.environ["PROFILE_MANUFACTURER"],
    "model": os.environ["PROFILE_MODEL"],
    "android_version": os.environ["PROFILE_ANDROID_VERSION"],
    "api_level": os.environ["PROFILE_API_LEVEL"],
    "screen_size": os.environ["PROFILE_SCREEN_SIZE"],
    "screen_density": os.environ["PROFILE_SCREEN_DENSITY"],
    "network_summary": os.environ["PROFILE_NETWORK"],
    "package_name": None,
    "build_variant": None,
    "app_data_cleared": False,
}
output.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

echo "$output"
