#!/bin/sh
# Build, sign and install the Vita Heart Watch app on the founder's Apple Watch, then launch it.
#
#   sh scripts/install_watch.sh
#
# The Watch is what makes the seated session real: HealthKit streams the wrist's own
# heart rate to /session/hr every five seconds, and the television stops saying
# "a recorded session" and says "live from your Apple Watch" instead.
#
# Needs, on the WATCH itself (not the iPhone):
#   Settings → Privacy & Security → Developer Mode → On → let it restart → confirm.
# Watch and iPhone unlocked, iPhone on the same Wi-Fi as this Mac.
set -e
cd "$(dirname "$0")/../watch"

# Find the watch rather than trust a hard-coded id: a re-pair issues a new one, and the
# old id fails in a way that reads like a build problem.
UDID="${WATCH_UDID:-}"
if [ -z "$UDID" ]; then
  TMP=$(mktemp -t vhwatch)
  xcrun devicectl list devices --json-output "$TMP" >/dev/null 2>&1 || true
  UDID=$(python3 - "$TMP" <<'PY'
import json, sys
try:
    devices = json.load(open(sys.argv[1]))["result"]["devices"]
except Exception:
    sys.exit(0)
for d in devices:
    hw = d.get("hardwareProperties", {})
    conn = d.get("connectionProperties", {})
    # A simulator reports transportType "sameMachine"; there is no isSimulated flag to
    # rely on, and picking a simulated watch fails later in a confusing way.
    if (hw.get("platform") == "watchOS"
            and conn.get("transportType") != "sameMachine"
            and conn.get("pairingState") == "paired"):
        print(hw.get("udid", ""))
        break
PY
)
  rm -f "$TMP"
fi
[ -n "$UDID" ] || { echo "No paired Apple Watch found. Unlock it, keep the iPhone nearby, and try again."; exit 1; }
echo "watch: $UDID"

# watchOS reports "Enabled (1)", not "Enabled": match the word, not the whole line.
MODE=$(xcrun devicectl device info details --device "$UDID" 2>/dev/null | sed -n 's/.*Developer Mode Status: *//p' | head -1)
case "$MODE" in
  Enabled*) ;;
  *)
  cat <<'STOP'
Developer Mode is off on the Watch, so nothing can be installed on it.

  On the WATCH (not the iPhone):
    Settings → Privacy & Security → Developer Mode → On
    It asks to restart. Let it restart, then confirm Developer Mode after it comes back.

  If "Developer Mode" is not in that menu, run this script once more first: the attempt
  is what makes watchOS show the entry.

Then run this script again. Nothing else about the demo depends on it — without the
Watch the session plays a recorded trace and says so on screen.
STOP
  exit 2 ;;
esac

xcodegen generate -q
xcodebuild -project VitaHeartWatch.xcodeproj -scheme VitaHeartWatch -destination 'generic/platform=watchOS' \
  -configuration Debug -derivedDataPath build/dd CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM=898978C87T \
  "CODE_SIGN_IDENTITY=Apple Development" "PROVISIONING_PROFILE_SPECIFIER=Vita Heart Watch Dev" build 2>&1 | grep -E "error:|BUILD"
APP=build/dd/Build/Products/Debug-watchos/VitaHeartWatch.app
codesign -d --entitlements :- "$APP" 2>/dev/null | grep -q "com.apple.developer.healthkit" && echo "entitlements: healthkit present"
xcrun devicectl device install app --device "$UDID" "$APP"
xcrun devicectl device process launch --device "$UDID" com.gravitilabs.vitaheart.watch || true
