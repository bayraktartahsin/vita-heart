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
# One window per OBS scene, and the two page titles differ, so the capture list is
# unambiguous. The prompter goes in Safari, a different application, so it can never be
# picked up by a browser capture.
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Google Chrome"
  activate
  set fam to make new window
  set URL of active tab of fam to "$FAMILY"
  set bounds of fam to {40, 60, 1480, 940}
  set alx to make new window
  set URL of active tab of alx to "$ALEXA"
  set bounds of alx to {80, 100, 1520, 980}
end tell
APPLESCRIPT
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Safari"
  activate
  make new document with properties {URL:"$PROMPTER"}
end tell
APPLESCRIPT

echo "5/5  heart-rate feed and pre-flight"
# Without a Watch on the wrist, the session still has to show real numbers moving. This
# feeds a recorded trace into any session the television opens, and the screen says
# "a recorded session" underneath for the whole time it plays.
pkill -f replay_daemon.py >/dev/null 2>&1 || true
("$PY" "$ROOT/scripts/replay_daemon.py" >/tmp/vitaheart-replay.log 2>&1 &)
"$PY" "$ROOT/scripts/preflight.py" || true

cat <<'NOTE'

────────────────────────────────────────────────────────────────────────
THREE scenes are recorded, one window is not.

  OBS scene   hotkey   one window source, filling the frame
  television  F1       vega-virtual-device
  family      F2       Chrome · "Vita Heart · Family"
  alexa       F3       Chrome · "Alexa+ · simulated surface · Vita Heart"

  NOT recorded         Safari · the prompter
                       → second screen, then Control-Command-F

One source per scene, and press Command-F on each so it fills the canvas.
Recording is one continuous take: press Start Recording once, then switch scenes
with F1, F2 and F3 as the prompter tells you. There is no terminal in the video.
In the prompter: click "voice on", allow the microphone, press the space bar.
────────────────────────────────────────────────────────────────────────
NOTE
