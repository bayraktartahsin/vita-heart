#!/bin/sh
# Stop everything demo_day started. Run this when you finish for the day.
#
#   sh scripts/stop_demo.sh
#
# Why it matters: the replay daemon, the director and every open page hold a poll against
# the API. Left running, that was most of a million Lambda invocations in two days — the
# whole monthly free tier — for a demo nobody was watching.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

pkill -f replay_daemon.py >/dev/null 2>&1 && echo "stopped the heart-rate feed" || echo "heart-rate feed: not running"
pkill -f obs_director.py  >/dev/null 2>&1 && echo "stopped the camera director" || echo "camera director: not running"
rm -f "$(python3 -c 'import tempfile,os;print(os.path.join(tempfile.gettempdir(),"vitaheart-replay.pid"))')" 2>/dev/null || true

osascript <<'APPLESCRIPT' >/dev/null 2>&1 || true
tell application "Google Chrome"
  repeat with w in (every window)
    try
      set u to URL of active tab of w
      if u contains "alexa-sim" or u contains "/family?household" then close w
    end try
  end repeat
end tell
APPLESCRIPT
osascript <<'APPLESCRIPT' >/dev/null 2>&1 || true
tell application "Safari"
  repeat with w in (every window)
    try
      if (URL of current tab of w) contains "prompter" then close w
    end try
  end repeat
end tell
APPLESCRIPT
echo "closed the family, Alexa and prompter windows"

echo
echo "The television is still running on the simulator; it polls once every 25 seconds."
echo "To stop that too:  vega virtual-device stop"
