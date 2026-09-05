"""The Reader: what is printed on a medicine box.

It reads. It does not identify. Identity comes from RxNorm afterwards, so every
fact can say where it came from. If a box is unreadable, the Reader says so;
it never completes a half-visible word.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

import boto3

from . import models

PROMPT = """You are reading the printed text on medicine packaging photographed at home.
Return ONLY a JSON array. One object per distinct medicine box visible, with keys:
  "name": the brand or generic name exactly as printed (string, or null if not legible),
  "strength": e.g. "500 mg" exactly as printed (string or null),
  "form": e.g. "tablet", "capsule", "syrup" (string or null),
  "directions": any dosing instruction printed or handwritten, verbatim (string or null),
  "lot": lot/batch number if printed (string or null),
  "legible": true if the name is clearly readable, false otherwise.
Copy every string character-for-character as printed: do not translate, localize, correct spelling, or expand abbreviations.
Do not guess a name from a partial word. Do not add medical advice. If no medicine box is visible return []."""


@dataclass
class BoxReading:
    name: str | None
    strength: str | None
    form: str | None
    directions: str | None
    lot: str | None
    legible: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _client():
    return boto3.client("bedrock-runtime", region_name=models.REGION)


def _parse(text: str) -> list[BoxReading]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    out = []
    for item in json.loads(m.group(0)):
        if not isinstance(item, dict):
            continue
        out.append(BoxReading(name=item.get("name"), strength=item.get("strength"), form=item.get("form"),
                              directions=item.get("directions"), lot=item.get("lot"),
                              legible=bool(item.get("legible", False)) and bool(item.get("name"))))
    return out


def read(image_bytes: bytes, fmt: str = "jpeg", model_id: str | None = None) -> list[BoxReading]:
    """One photo in, a list of readings out. `fmt` is jpeg or png."""
    r = _client().converse(
        modelId=model_id or models.READER_MODEL,
        messages=[{"role": "user", "content": [{"image": {"format": fmt, "source": {"bytes": image_bytes}}},
                                                {"text": PROMPT}]}],
        inferenceConfig={"maxTokens": 800, "temperature": 0},
    )
    return _parse(r["output"]["message"]["content"][0]["text"])
