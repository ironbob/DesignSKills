#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <adb-serial> <package-name> <output-file>" >&2
  exit 2
fi

serial="$1"
package_name="$2"
output="$3"
mkdir -p "$(dirname "$output")"

pid="$(adb -s "$serial" shell pidof "$package_name" 2>/dev/null | tr -d '\r' || true)"

if [[ -n "$pid" ]]; then
  adb -s "$serial" logcat -d --pid "$pid" -v threadtime > "$output" || true
else
  adb -s "$serial" logcat -d -v threadtime | grep "$package_name" > "$output" || true
fi

echo "$output"
