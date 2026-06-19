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
wm_size="$("${adb_cmd[@]}" shell wm size 2>/dev/null | tr -d '\r' | sed 's/"/\\"/g' || true)"
wm_density="$("${adb_cmd[@]}" shell wm density 2>/dev/null | tr -d '\r' | sed 's/"/\\"/g' || true)"
network="$("${adb_cmd[@]}" shell dumpsys connectivity 2>/dev/null | grep -E 'NetworkAgentInfo|Active default network|mNetworkInfo' | head -20 | sed 's/"/\\"/g' | tr '\n' ';' || true)"

cat > "$output" <<JSON
{
  "adb_serial": "$serial",
  "manufacturer": "$manufacturer",
  "model": "$model",
  "android_version": "$android_version",
  "api_level": "$api_level",
  "screen_size": "$wm_size",
  "screen_density": "$wm_density",
  "network_summary": "$network"
}
JSON

echo "$output"
