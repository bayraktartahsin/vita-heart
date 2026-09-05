#!/usr/bin/env python3
"""Post signed, synthetic Ring webhooks to the API, the way Ring's own delivery would.

    python scripts/ring_simulate.py night        # door opens 03:10, hall 16 C for two hours, nothing else
    python scripts/ring_simulate.py quiet        # no motion all morning (posts nothing but a device_online)
    python scripts/ring_simulate.py event motion_detected --device "hall camera"

The HMAC key is read from the file named by VITAHEART_RING_KEYS_FILE (default:
the founder's keys-ring.env outside the repo). Nothing here is a real Ring
event, and the family summary says "signals" not "Ring recorded"; the demo video
says so out loud.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

API = os.environ.get("VITAHEART_API", "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com")
KEYS = Path(os.environ.get("VITAHEART_RING_KEYS_FILE", Path.home() / "Documents/New Apps/Hackhaton/AmazonAppDev2026/keys-ring.env"))


def key() -> bytes:
    for line in KEYS.read_text().splitlines():
        if line.startswith("RING_HMAC_SIGNATURE_KEY="):
            return line.split("=", 1)[1].strip().encode()
    sys.exit("no RING_HMAC_SIGNATURE_KEY in keys file")


def send(household: str, payload: dict) -> None:
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(key(), body, hashlib.sha256).hexdigest()
    r = httpx.post(f"{API}/ring/webhook", params={"household": household}, content=body,
                   headers={"content-type": "application/json", "X-Signature": sig}, timeout=30)
    print(payload["event_type"], payload.get("device_name", ""), payload.get("timestamp", ""), "->", r.status_code, r.text[:80])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=["night", "quiet", "event"])
    ap.add_argument("event_type", nargs="?")
    ap.add_argument("--device", default="front door")
    ap.add_argument("--household", default="AHMET1")
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    rid = lambda n: f"sim-{now:%Y%m%d}-{n}"  # noqa: E731
    if a.scenario == "event":
        send(a.household, {"event_type": a.event_type, "device_name": a.device, "timestamp": now.isoformat(), "meta": {"request_id": rid(now.strftime('%H%M%S'))}})
        return
    if a.scenario == "night":
        t0310 = (now - timedelta(hours=3)).replace(hour=0, minute=10, second=0, microsecond=0)  # 03:10 Istanbul today
        send(a.household, {"event_type": "contact_opened", "device_name": "front door", "timestamp": t0310.isoformat(), "meta": {"request_id": rid("door-open")}})
        send(a.household, {"event_type": "contact_closed", "device_name": "front door", "timestamp": (t0310 + timedelta(minutes=2)).isoformat(), "meta": {"request_id": rid("door-close")}})
        for i, temp in enumerate([16.8, 16.4, 16.1, 16.3, 15.9]):
            t = (now - timedelta(hours=3)).replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(minutes=30 * i)
            send(a.household, {"event_type": "temperature_reading", "device_name": "hall sensor", "timestamp": t.isoformat(), "data": {"temperature_c": temp}, "meta": {"request_id": rid(f"temp-{i}")}})
    if a.scenario == "quiet":
        send(a.household, {"event_type": "device_online", "device_name": "hall camera", "timestamp": now.isoformat(), "meta": {"request_id": rid("online")}})


if __name__ == "__main__":
    main()
