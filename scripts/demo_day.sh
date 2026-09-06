#!/bin/sh
# Everything the recording needs, in one command. Run it, wait for READY, then press record.
#
#   sh scripts/demo_day.sh
#
# It puts the household into the demo state with a dose due right now, checks all
# thirteen surfaces, starts the simulator if it is not running, launches the app,
# and opens the three pages the script uses. It never touches the camera or OBS.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
API="https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
export PATH="$HOME/vega/bin:$PATH"

echo "1/5  simulator"
if ! vega virtual-device status 2>/dev/null | grep -q '"running":true'; then
  vega virtual-device start --gui --timeout 300
fi

echo "2/5  the app"
( cd "$ROOT/tv" && npm run build:debug >/tmp/vitaheart-build.log 2>&1 )
vega run-app "$ROOT/tv/build/aarch64-debug/vitahearttv_aarch64.vpkg"

echo "3/5  demo state (a dose becomes due now)"
"$PY" "$ROOT/scripts/demo_setup.py" --due-now

echo "4/5  pages"
open -a "Google Chrome" "$API/alexa-sim"
open -a "Google Chrome" "$API/family?household=AHMET1"
open "$ROOT/docs/teleprompter.html"

echo "5/5  pre-flight"
"$PY" "$ROOT/scripts/preflight.py"
echo
echo "Now: OBS -> Start Recording, then space on the teleprompter, then speak."
