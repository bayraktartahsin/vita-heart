#!/usr/bin/env python3
"""Put the demo household into the state the video starts from. Idempotent; takes about a minute.

    python scripts/demo_setup.py

1. reset AHMET1 (keeps the profile)         4. Ring night scenario (signed synthetic webhooks)
2. read one rendered CORASPIN label          5. Night Watch without email
3. set the household clock (08:00 / 19:00)
Everything synthetic is labelled as such on the television and in the summary wording.
"""
from __future__ import annotations

import io
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
API = "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
HH = "AHMET1"


def label_png(lines: list[str]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 420), "white")
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 64)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40)
    except OSError:
        big = small = ImageFont.load_default()
    y = 30
    for i, line in enumerate(lines):
        d.text((40, y), line, fill="black", font=big if i == 0 else small)
        y += 90 if i == 0 else 60
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()


def step(msg): print(f"• {msg}", flush=True)


def main() -> None:
    py = sys.executable
    step("reset"); subprocess.run([py, str(ROOT / "scripts/reset_demo.py")], check=True, capture_output=True)
    for lines in (["CORASPIN 100 mg", "30 enterik tablet", "Günde 1 kez, sabah", "LOT 25A007"],
                  ["GLIFOR 850 mg", "60 film tablet", "Sabah ve akşam, yemekten sonra", "LOT 24H331"]):
        png = label_png(lines)
        up = httpx.post(f"{API}/meds/upload-url", json={"household": HH, "content_type": "image/png"}, timeout=30).json()
        httpx.put(up["url"], content=png, headers={"content-type": "image/png"}, timeout=60).raise_for_status()
        t = time.time()
        r = httpx.post(f"{API}/meds/read", json={"household": HH, "key": up["key"]}, timeout=120).json()
        for m in r["meds"]:
            step(f"read {lines[0]} -> {m['status']} {m.get('name')} = {(m.get('identity') or {}).get('name')} ({len(m['recalls'])} recalls, slots {m['directions']['slots']}) in {time.time()-t:.1f}s on {r.get('ran_on')}")
    step("clock"); httpx.post(f"{API}/clock", json={"household": HH, "times": {"morning": "08:00", "evening": "19:00"}}, timeout=30).raise_for_status()
    step("ring night scenario"); subprocess.run([py, str(ROOT / "scripts/ring_simulate.py"), "night"], check=True, capture_output=True)
    step("night watch"); out = httpx.post(f"{API}/night/run", json={"household": HH, "notify": False}, timeout=120).json()
    print("  ", out["text"])
    b = httpx.get(f"{API}/board", params={"household": HH}, timeout=30).json()
    step(f"board: {len(b['dueDoses'])} dose(s) today, clock {b['clock']}")


if __name__ == "__main__":
    main()
