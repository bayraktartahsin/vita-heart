#!/bin/sh
# Recording day, one command. Opens exactly the windows the take needs and checks them.
#
#   sh scripts/demo_day.sh
#
# Opens FIVE windows:
#   1 Vega Virtual Device  · the television          → OBS scene TV        (F1)
#   2 Chrome "Family"      · the family's page       → OBS scene FAMILY    (F2)
#   3 Chrome "Alexa"       · the Alexa+ surface      → OBS scene ALEXA     (F3)
#   4 Terminal             · this window             → OBS scene TERMINAL  (F4)
#   5 Chrome "Prompter"    · what you read           → NOT captured. Drag to your second screen.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
API="https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
export PATH="$HOME/vega/bin:$PATH"

echo "1/5  television"
if ! vega virtual-device status 2>/dev/null | grep -q '"running":true'; then
  vega virtual-device start --gui --timeout 300
fi

echo "2/5  the app"
( cd "$ROOT/tv" && npm run build:debug >/tmp/vitaheart-build.log 2>&1 ) || { echo "build failed, see /tmp/vitaheart-build.log"; exit 1; }
vega run-app "$ROOT/tv/build/aarch64-debug/vitahearttv_aarch64.vpkg"

echo "3/5  demo state (a tablet becomes due now)"
"$PY" "$ROOT/scripts/demo_setup.py" --due-now

echo "4/5  windows"
# -n --args --new-window forces a separate Chrome window per page; tabs cannot be captured
# individually by OBS, and the take switches between them.
open -na "Google Chrome" --args --new-window "$API/family?household=AHMET1"
sleep 2
open -na "Google Chrome" --args --new-window "$API/alexa-sim"
sleep 2
open -na "Google Chrome" --args --new-window "$API/prompter?household=AHMET1"

echo "5/5  pre-flight"
"$PY" "$ROOT/scripts/preflight.py" || true

cat <<'NOTE'

────────────────────────────────────────────────────────────────────────
FIVE windows are open. Four are recorded, one is not.

  OBS scene   hotkey   window to capture
  TV          F1       Vega Virtual Device
  FAMILY      F2       Chrome · Vita Heart · Family
  ALEXA       F3       Chrome · Vita Heart · Alexa
  TERMINAL    F4       this Terminal window

  NOT captured        Chrome · Vita Heart · prompter
                      → drag it to your second screen, then Control-Command-F

In the prompter: click "voice on", allow the microphone, press the space bar.
It counts you in and then tells you when to speak, when to press, when to wait.
────────────────────────────────────────────────────────────────────────
NOTE
