"""Live test against Bedrock: renders a fake box label and asks the Reader to read it.

Skipped when AWS credentials are not real (CI). Run locally: pytest tests/test_reader_live.py -s
"""
import io
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.skipif(not os.environ.get("VITAHEART_LIVE"), reason="set VITAHEART_LIVE=1 to call Bedrock")


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
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_reader_reads_a_clear_label():
    from agents import reader
    png = label_png(["PARACETAMOL 500 mg", "20 film tablet", "Günde 2 kez, yemekten sonra", "LOT 24K118"])
    boxes = reader.read(png, fmt="png")
    assert len(boxes) == 1, boxes
    b = boxes[0]
    assert b.legible and "paracetamol" in (b.name or "").lower()
    assert "500" in (b.strength or "")
    assert b.directions and "2" in b.directions
    assert (b.lot or "").upper().endswith("24K118")


def test_reader_does_not_invent_a_name_from_a_blank_image():
    from agents import reader
    png = label_png([" "])
    boxes = reader.read(png, fmt="png")
    assert all(not b.legible for b in boxes)
