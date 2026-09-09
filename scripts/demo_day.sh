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
FAMILY="$API/family?household=AHMET1"
ALEXA="$API/alexa-sim"
PROMPTER="$API/prompter?household=AHMET1"
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
# One Chrome window with two tabs, not two windows: OBS cannot tell two identical Chrome
# windows apart, and a wrong capture is discovered only in the recording. The prompter goes
# in Safari, a different application, so nothing can be confused for it.
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Google Chrome"
  activate
  set w to make new window
  set URL of active tab of w to "$FAMILY"
  tell w to make new tab with properties {URL:"$ALEXA"}
  set bounds of w to {40, 60, 1480, 940}
end tell
APPLESCRIPT
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Safari"
  activate
  make new document with properties {URL:"$PROMPTER"}
end tell
APPLESCRIPT

echo "5/5  pre-flight"
"$PY" "$ROOT/scripts/preflight.py" || true

cat <<'NOTE'

────────────────────────────────────────────────────────────────────────
THREE things are recorded, one is not.

  OBS scene   hotkey   one source, filling the frame
  TV          F1       window · vega-virtual-device
  WEB         F2       window · Google Chrome   (⌘1 family · ⌘2 Alexa)
  TERMINAL    F3       window · Terminal

  NOT recorded         Safari · the prompter
                       → second screen, then Control-Command-F

One source per scene, and press Command-F on each so it fills the canvas.
In the prompter: click "voice on", allow the microphone, press the space bar.
────────────────────────────────────────────────────────────────────────
NOTE
