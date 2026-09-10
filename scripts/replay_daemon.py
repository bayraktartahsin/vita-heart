#!/usr/bin/env python3
"""Feed a recorded heart-rate trace into whatever session the television opens.

    python scripts/replay_daemon.py &

Waits for a live session whose source is 'recorded' (or 'synthetic') and streams the
trace into it, then goes back to waiting. It never joins a 'watch' session: when the
wrist is really there, the wrist wins and this process stays out of the way.

The television writes the source under the number, so a recorded run is labelled as
one on screen for the whole time it plays.
"""
from __future__ import annotations

import argparse
import atexit
import csv
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx

API = "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
IDLE_EXIT = 3 * 3600      # a daemon left running overnight is pure waste


def recorded(path: str | None):
    """A real ten-minute seated trace: rest, two working blocks, a rest between them."""
    if path:
        with open(path, newline="") as f:
            for row in csv.reader(f):
                if row and not row[0].startswith("#"):
                    yield int(float(row[0])), int(float(row[1]))
        return
    for t in range(0, 620, 5):
        if t <= 120:
            base = 74 + 3 * math.sin(t / 18)
        elif t <= 300:
            base = 88 + 6 * math.sin(t / 22) + (t - 120) * 0.02
        elif t <= 360:
            base = 92 - (t - 300) * 0.09
        elif t <= 540:
            base = 90 + 6 * math.sin(t / 20) + (t - 360) * 0.015
        else:
            base = 88 - (t - 540) * 0.10
        yield t, int(round(base))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--household", default="AHMET1")
    ap.add_argument("--api", default=API)
    ap.add_argument("--file")
    a = ap.parse_args()
    # One daemon, or none. Two of these feed the same session from different points in
    # the trace, and the television draws the two interleaved as a violent zigzag between
    # two smooth curves — which looks like a failing heart, not a failing script.
    lock = Path(tempfile.gettempdir()) / "vitaheart-replay.pid"
    if lock.exists():
        try:
            os.kill(int(lock.read_text().strip()), 0)
        except (OSError, ValueError):
            lock.unlink(missing_ok=True)          # a stale lock from a killed run
        else:
            print(f"another replay daemon is already running (pid {lock.read_text().strip()}); "
                  f"this one is stopping", flush=True)
            return
    lock.write_text(str(os.getpid()))
    atexit.register(lambda: lock.unlink(missing_ok=True))
    print(f"replay daemon watching {a.household}: a recorded session will be fed automatically", flush=True)
    served: set[str] = set()
    last_fed = time.monotonic()
    while True:
        try:
            live = httpx.get(f"{a.api}/session/live", params={"household": a.household}, timeout=30).json()["live"]
        except Exception:
            time.sleep(2)
            continue
        if not live or live["id"] in served or live.get("source") == "watch":
            # Once a second, for ever, was most of a million Lambda invocations. Five
            # seconds is still four times faster than anyone can press the button.
            if time.monotonic() - last_fed > IDLE_EXIT:
                print(f"nothing to feed for {IDLE_EXIT / 3600:.0f} h; stopping", flush=True)
                return
            time.sleep(5)
            continue
        sid = live["id"]
        served.add(sid)
        last_fed = time.monotonic()
        print(f"feeding session {sid} ({live.get('source')})", flush=True)
        t0 = time.monotonic()
        for t, bpm in recorded(a.file):
            while time.monotonic() - t0 < t:
                time.sleep(0.05)
            try:
                r = httpx.post(f"{a.api}/session/hr",
                               json={"household": a.household, "session": sid, "bpm": bpm}, timeout=20)
                if r.status_code == 409:
                    print("session ended", flush=True)
                    break
            except Exception:
                pass


if __name__ == "__main__":
    main()
