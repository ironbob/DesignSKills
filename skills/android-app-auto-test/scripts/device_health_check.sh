#!/usr/bin/env bash
# Health gate run before each path in a batch. Exit 0 = healthy; non-zero with a
# reason on stderr = ENVIRONMENT_ERROR (the dispatcher retries with backoff per
# inputs.env_retry instead of marking the path blocked).
#
# Usage: device_health_check.sh <adb-serial> <package-name> [max-crashes]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <adb-serial> <package-name> [max-crashes]" >&2
  exit 2
fi

serial="$1"
package_name="$2"
max_crashes="${3:-3}"

state="$(adb -s "$serial" get-state 2>/dev/null | tr -d '\r' || true)"
if [[ "$state" != "device" ]]; then
  echo "device not reachable: get-state='$state' (serial=$serial); attempting reconnect" >&2
  adb -s "$serial" reconnect 2>/dev/null || true
  sleep 2
  state="$(adb -s "$serial" get-state 2>/dev/null | tr -d '\r' || true)"
  if [[ "$state" != "device" ]]; then
    echo "reconnect failed for $serial" >&2
    exit 3
  fi
fi

if ! adb -s "$serial" shell pm path "$package_name" >/dev/null 2>&1; then
  echo "package not installed: $package_name" >&2
  exit 4
fi

# Crash/ANR loop guard (best-effort heuristic over dropbox).
crashes="$(adb -s "$serial" shell dumpsys dropbox --print 2>/dev/null \
  | grep -Ec '^(data_|system_)?(crash|anr)' || true)"
crashes="${crashes:-0}"
if [[ "$crashes" -gt "$max_crashes" ]]; then
  echo "crash/anr loop suspected: ${crashes} entries in dropbox (max ${max_crashes})" >&2
  exit 5
fi

wake="$(adb -s "$serial" shell dumpsys power 2>/dev/null \
  | grep -E 'mWakefulness|mScreenOn' | head -1 | tr -d '\r' || true)"
echo "ok serial=$serial package=$package_name wakefulness='${wake}' crashes=${crashes}"
exit 0
