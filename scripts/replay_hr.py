#!/usr/bin/env python3
"""Replay a recorded heart-rate trace into a live session, labelled honestly.

    python scripts/replay_hr.py --file docs/proof/hr-2026-09-12.csv        # a real export: source "recorded"
    python scripts/replay_hr.py --synthetic                                  # development only: source "synthetic"

The CSV has two columns: seconds_since_start, bpm (a HealthKit export reduced
with scripts/healthkit_to_csv.py). The television shows the source next to the
number, so a recorded or synthetic signal is never mistaken for a live wrist.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time

import httpx

API = "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"


def synthetic(seconds: int = 600):
    """A shape for development only: gentle rise in work blocks, fall in rest. Labelled 'synthetic' on the TV."""
    for t in range(0, seconds, 5):
        base = 78
        if 120 < t <= 300 or 360 < t <= 540:
            base = 94 + 4 * math.sin(t / 25)
        elif 300 < t <= 360:
            base = 86
        yield t, int(round(base + (t % 7) * 0.4))


def from_csv(path: str):
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            yield int(float(row[0])), int(float(row[1]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--household", default="AHMET1")
    ap.add_argument("--api", default=API)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--synthetic", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0, help="2.0 replays twice as fast")
    a = ap.parse_args()

    source = "recorded" if a.file else "synthetic"
    live = httpx.get(f"{a.api}/session/live", params={"household": a.household}, timeout=30).json()["live"]
    if not live:
        print("The television has not started a session. Start one on the TV first.", file=sys.stderr)
        sys.exit(2)
    if live["source"] != source:
        print(f"The television started a '{live['source']}' session; this replay is '{source}'. Refusing to mislabel.", file=sys.stderr)
        sys.exit(3)
    samples = from_csv(a.file) if a.file else synthetic()
    t0 = time.monotonic()
    for t, bpm in samples:
        while (time.monotonic() - t0) * a.speed < t:
            time.sleep(0.05)
        r = httpx.post(f"{a.api}/session/hr", json={"household": a.household, "session": live["id"], "bpm": bpm}, timeout=30)
        print(f"t={t:4d}s bpm={bpm:3d} -> {r.status_code}", flush=True)
        if r.status_code == 409:
            print("session ended on the television", file=sys.stderr)
            break


if __name__ == "__main__":
    main()
