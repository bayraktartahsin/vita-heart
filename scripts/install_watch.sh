#!/bin/sh
# Build, sign and install the Vita Heart Watch app on the founder's Apple Watch, then launch it.
# Requires: Watch Developer Mode ON (and restarted once after enabling), Watch and iPhone unlocked,
# iPhone on the same Wi-Fi as this Mac. Profile "Vita Heart Watch Dev" is already installed locally.
set -e
cd "$(dirname "$0")/../watch"
WATCH="${WATCH_UDID:-3C5BCF96-B132-5C19-9E18-32EFDB23F4A9}"
xcodegen generate -q
xcodebuild -project VitaHeartWatch.xcodeproj -scheme VitaHeartWatch -destination 'generic/platform=watchOS' \
  -configuration Debug -derivedDataPath build/dd CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM=898978C87T \
  "CODE_SIGN_IDENTITY=Apple Development" "PROVISIONING_PROFILE_SPECIFIER=Vita Heart Watch Dev" build 2>&1 | grep -E "error:|BUILD"
APP=build/dd/Build/Products/Debug-watchos/VitaHeartWatch.app
codesign -d --entitlements :- "$APP" 2>/dev/null | grep -q "com.apple.developer.healthkit" && echo "entitlements: healthkit present"
xcrun devicectl device info details --device "$WATCH" 2>/dev/null | grep -i developerModeStatus
xcrun devicectl device install app --device "$WATCH" "$APP"
xcrun devicectl device process launch --device "$WATCH" com.gravitilabs.vitaheart.watch || true
