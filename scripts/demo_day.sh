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

echo "1/7  television"
if ! vega virtual-device status 2>/dev/null | grep -q '"running":true'; then
  vega virtual-device start --gui --timeout 300
fi

echo "2/7  the app"
( cd "$ROOT/tv" && npm run build:debug >/tmp/vitaheart-build.log 2>&1 ) || { echo "build failed, see /tmp/vitaheart-build.log"; exit 1; }
vega run-app "$ROOT/tv/build/aarch64-debug/vitahearttv_aarch64.vpkg"

echo "3/7  waking the agents"
# A runtime that has just been deployed answers its first call slowly, and the first call
# on recording day should not be the one that builds the demo.
curl -s -m 120 -X POST "$API/session/coach" -H 'content-type: application/json' \
  -d '{"household":"AHMET1","numbers":{"phase":"warm","lastBpm":70}}' >/dev/null 2>&1 || true

echo "4/7  demo state (a tablet becomes due now)"
"$PY" "$ROOT/scripts/demo_setup.py" --due-now

echo "5/7  windows"
# One window per OBS scene, and the two page titles differ, so the capture list is
# unambiguous. The prompter goes in Safari, a different application, so it can never be
# picked up by a browser capture.
#
# These windows are REUSED, never closed and remade. An OBS window capture holds a
# numeric window id: close the window and the scene is pointing at a window that no
# longer exists, which looks fine in the source list and records nothing.
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
on ensure(matchText, theURL, x1, y1, x2, y2)
  tell application "Google Chrome"
    set keep to missing value
    -- a window without a normal active tab throws here; one bad window must not
    -- abort the whole script and leave the take with no pages at all
    repeat with w in (every window)
      try
        if (title of active tab of w) contains matchText then
          if keep is missing value then
            set keep to w
          else
            close w
          end if
        end if
      end try
    end repeat
    if keep is missing value then set keep to (make new window)
    set URL of active tab of keep to theURL
    set bounds of keep to {x1, y1, x2, y2}
  end tell
end ensure

tell application "Google Chrome" to activate
my ensure("Family", "$FAMILY", 40, 60, 1480, 940)
my ensure("Alexa+", "$ALEXA", 80, 100, 1520, 980)
APPLESCRIPT
osascript <<APPLESCRIPT >/dev/null 2>&1 || true
tell application "Safari"
  activate
  repeat with w in (every window)
    try
      if name of w contains "prompter" then close w
    end try
  end repeat
  make new document with properties {URL:"$PROMPTER"}
end tell
APPLESCRIPT

echo "6/7  the camera"
# OBS follows the prompter: it aims each scene at its window, fits it to the frame,
# and switches scene on cue. Without OBS listening this prints how to turn it on and
# the take carries on with F1/F2/F3 by hand.
"$PY" -c "import websockets" 2>/dev/null || "$PY" -m pip install -q websockets
pkill -f obs_director.py >/dev/null 2>&1 || true
"$PY" "$ROOT/scripts/obs_director.py" --setup || true
("$PY" "$ROOT/scripts/obs_director.py" >/tmp/vitaheart-director.log 2>&1 &)

echo "7/7  heart-rate feed and pre-flight"
# Without a Watch on the wrist, the session still has to show real numbers moving. This
# feeds a recorded trace into any session the television opens, and the screen says
# "a recorded session" underneath for the whole time it plays.
pkill -f replay_daemon.py >/dev/null 2>&1 || true
("$PY" "$ROOT/scripts/replay_daemon.py" >/tmp/vitaheart-replay.log 2>&1 &)
"$PY" "$ROOT/scripts/preflight.py" || true

cat <<'NOTE'

────────────────────────────────────────────────────────────────────────
ONE key press records the whole thing.

  In the prompter (Safari, second screen): click "voice on", then press SPACE.

  From there it runs itself. OBS starts recording, the scene changes on cue,
  the television checks in, opens the medicines, confirms the tablet, starts
  and stops the session and opens the family page. At the end the recording
  stops on its own and the file is in ~/Movies.

  You read the white sentences. That is all.

  Scenes are aimed automatically. If the camera is NOT following, OBS is not
  listening: Tools → WebSocket Server Settings → tick "Enable WebSocket
  server" → OK, then run this script again. Until then, press F1/F2/F3 as the
  grey SCENE badge in the prompter changes.

  Not recorded: Safari, the prompter. Keep it on the second screen.
────────────────────────────────────────────────────────────────────────
NOTE
