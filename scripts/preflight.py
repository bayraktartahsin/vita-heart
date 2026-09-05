#!/usr/bin/env python3
"""Pre-flight before recording or judging. Every line is a real check, not a hope.

    python scripts/preflight.py
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

API = os.environ.get("VITAHEART_API", "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com")
HH = "AHMET1"
ok_all = True


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK ' if cond else 'FAIL'} {name}{(': ' + detail) if detail else ''}", flush=True)


def main() -> None:
    t = time.time(); h = httpx.get(f"{API}/health", timeout=30); check("API health", h.status_code == 200, f"{(time.time()-t)*1000:.0f} ms")
    b = httpx.get(f"{API}/board", params={"household": HH}, timeout=30).json()
    check("board loads", "greeting" in b, b.get("greeting", ""))
    due = [d for d in b["dueDoses"] if not d["unscheduled"]]
    check("a dose is due now (for the Medication Moment scene)", bool(due), ", ".join(f"{d['name']} {d['slot']}" for d in due) or "none; run demo_setup.py --due-now")
    check("clock set", bool(b.get("clock")), str(b.get("clock")))
    meds = httpx.get(f"{API}/meds", params={"household": HH}, timeout=30).json()["meds"]
    check("medicines identified", any(m.get("status") == "identified" for m in meds), ", ".join(str(m.get("name")) for m in meds))
    s = httpx.get(f"{API}/family/summary", params={"household": HH}, timeout=30).json()["summary"]
    check("night watch summary exists", bool(s), (s or {}).get("text", "")[:80])
    t = time.time(); c = httpx.post(f"{API}/session/coach", json={"household": HH, "numbers": {"phase": "warm", "elapsedSeconds": 1, "lastBpm": 70, "zone": {"workFloor": 79, "workCeiling": 103}}}, timeout=90).json()
    check("fleet on AgentCore warm (coach line)", bool(c.get("line")) and not c.get("fallback"), f"{(time.time()-t):.1f} s")
    check("no live session left open", httpx.get(f"{API}/session/live", params={"household": HH}, timeout=30).json()["live"] is None)
    anon = httpx.post(f"{API}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, timeout=30)
    check("MCP anonymous = bare 401", anon.status_code == 401 and "www-authenticate" not in {k.lower() for k in anon.headers})
    verifier = secrets.token_urlsafe(48); challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    with httpx.Client(follow_redirects=False, timeout=30) as cl:
        r = cl.post(f"{API}/oauth/approve", params={"client_id": "vita-heart-alexa", "redirect_uri": API + "/alexa-sim", "code_challenge": challenge, "state": "pf"}, data={"household": HH})
        code = httpx.URL(r.headers.get("location", "")).params.get("code")
        tok = cl.post(f"{API}/oauth/token", data={"grant_type": "authorization_code", "code": code or "", "code_verifier": verifier, "client_id": "vita-heart-alexa", "redirect_uri": API + "/alexa-sim"}).json().get("access_token")
        check("OAuth PKCE issues a token", bool(tok))
        t = time.time(); tr = cl.post(f"{API}/alexa-sim/turn", headers={"authorization": f"Bearer {tok}"}, json={"utterance": "How is Dad doing today?"}, timeout=90).json()
        check("Alexa turn answers", bool(tr.get("speech")), f"{tr.get('tool')} in {(time.time()-t):.1f} s")
    vega = shutil.which("vega") or os.path.expanduser("~/vega/bin/vega")
    if os.path.exists(vega):
        st = subprocess.run([vega, "virtual-device", "status"], capture_output=True, text=True).stdout
        check("Vega Virtual Device running", '"running":true' in st)
        r = subprocess.run([vega, "device", "installed-apps"], capture_output=True, text=True, timeout=90)
        apps = r.stdout + r.stderr   # the CLI writes the list to stdout but progress lines to stderr; accept either
        check("Vita Heart installed on the device", "com.gravitilabs.vitaheart.main" in apps, "" if "com.gravitilabs.vitaheart.main" in apps else (apps.strip()[:80] or "no output"))
    else:
        check("vega CLI present", False, "source ~/vega/env")
    now_ist = datetime.now(timezone.utc) + timedelta(hours=3)
    print(f"     Istanbul time {now_ist:%H:%M}; morning slot window is 07:30 to 10:00 for an 08:00 clock")
    print("READY" if ok_all else "NOT READY")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
