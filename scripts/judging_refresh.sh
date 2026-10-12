#!/bin/sh
# Keep the demo household presentable while the judges are looking.
#
#   sh scripts/judging_refresh.sh
#
# A dose is only "due" for about two and a half hours around its slot, and the slot is
# whatever time this was last run. Outside that the television honestly says "Nothing due
# right now" — correct, but the quietest possible first impression. Judging runs 9-20 Nov
# 2026, so this runs each of those mornings in Seattle and leaves a live board, fresh
# medicines with live recalls, and a message that is not two months old.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
API="https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"

echo "=== judging refresh $(date -u '+%Y-%m-%d %H:%M UTC') ==="

# The fleet sleeps. Its first call after a long idle is slow, and that call should not be
# the one rebuilding the demo.
echo "1/3  waking the agents"
curl -s -m 150 -X POST "$API/session/coach" -H 'content-type: application/json' \
  -d '{"household":"AHMET1","numbers":{"phase":"warm","lastBpm":70}}' >/dev/null 2>&1 || true

echo "2/3  rebuilding the demo state"
"$PY" "$ROOT/scripts/demo_setup.py" --due-now

echo "3/3  checking a judge would now see a live board"
"$PY" - <<'PY'
import json, sys, urllib.request
API = "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
b = json.load(urllib.request.urlopen(f"{API}/board?household=AHMET1"))
due = [d for d in b.get("dueDoses", []) if not d.get("unscheduled")]
meds = json.load(urllib.request.urlopen(f"{API}/meds?household=AHMET1"))["meds"]
ident = [m for m in meds if m.get("status") == "identified"]
steps = json.load(urllib.request.urlopen(f"{API}/trace?household=AHMET1"))["steps"]
print(f"     board    : {b.get('greeting')} | clock {b.get('clock')}")
print(f"     due now  : {', '.join(d['name'] + ' ' + d['slot'] for d in due) or 'NONE'}")
print(f"     medicines: {len(ident)} identified | agent trace: {len(steps)} tool calls")
ok = bool(due) and len(ident) >= 2 and len(steps) >= 4
print("READY — a judge opening it now sees a live board" if ok else "NOT READY — check the lines above")
sys.exit(0 if ok else 1)
PY
