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
Return ONLY a JSON object with two keys:
  "transcript": every piece of text you can actually see in the image, verbatim, joined with " | " (empty string if there is no text),
  "boxes": a JSON array, one object per distinct medicine box visible, with keys:
  "name": the brand or generic name exactly as printed (string, or null if not legible),
  "strength": e.g. "500 mg" exactly as printed (string or null),
  "form": e.g. "tablet", "capsule", "syrup" (string or null),
  "directions": any dosing instruction printed or handwritten, verbatim (string or null),
  "lot": lot/batch number if printed (string or null),
  "legible": true if the name is clearly readable, false otherwise.
Copy every string character-for-character as printed: do not translate, localize, correct spelling, or expand abbreviations.
Every value in "boxes" must also appear inside "transcript". Do not guess a name from a partial word. Do not add medical advice.
If the image has no readable text, return {"transcript": "", "boxes": []}."""


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


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşü]", "", s.lower())


def _parse(text: str) -> list[BoxReading]:
    """Accept a box only if its name is literally present in the model's own transcript.

    Vision models complete a blank or blurry image into a plausible medicine
    (Nova Lite produced "Ibuprofen 200 mg" from a white rectangle). Requiring
    the name to appear in the verbatim transcript removes that failure class:
    a made-up name has no text to be copied from.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    transcript = _norm(str(data.get("transcript") or ""))
    out = []
    for item in data.get("boxes") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        grounded = bool(name) and bool(transcript) and _norm(str(name)) in transcript
        out.append(BoxReading(name=name if grounded else None, strength=item.get("strength") if grounded else None,
                              form=item.get("form") if grounded else None,
                              directions=item.get("directions") if grounded else None,
                              lot=item.get("lot") if grounded else None,
                              legible=grounded and bool(item.get("legible", False))))
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
