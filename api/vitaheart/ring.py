"""Ring webhooks in, calm signals out.

Ring signs every webhook with HMAC-SHA256 over the raw body using the app's
HMAC Signature Key; the hex digest arrives in `X-Signature` as `sha256=<hex>`.
A request whose signature does not verify is answered 401 and stored nowhere.
`meta.request_id` makes delivery idempotent: the same id twice is one signal.

Event names are normalised to a small vocabulary the Night Watch rules read:
  motion · doorbell.press · contact.open · contact.close · temperature ·
  humidity · air.alert · device.online · device.offline · ring.<other>
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from . import store

_KNOWN = {
    "motion_detected": "motion",
    "button_press": "doorbell.press",
    "ding": "doorbell.press",
    "contact_opened": "contact.open",
    "contact_closed": "contact.close",
    "device_online": "device.online",
    "device_offline": "device.offline",
    "temperature_reading": "temperature",
    "humidity_reading": "humidity",
    "air_quality_alert": "air.alert",
}


def hmac_key() -> bytes | None:
    k = os.environ.get("VITAHEART_RING_HMAC_KEY")
    return k.encode("utf-8") if k else None


def sign(body: bytes, key: bytes) -> str:
    return "sha256=" + hmac.new(key, body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str | None, key: bytes | None) -> bool:
    if not key or not signature:
        return False
    expected = sign(body, key)
    return hmac.compare_digest(expected, signature.strip())


def normalise(payload: dict[str, Any]) -> dict[str, Any]:
    et = str(payload.get("event_type") or payload.get("type") or "").lower()
    kind = _KNOWN.get(et, f"ring.{et or 'unknown'}")
    device = payload.get("device_name") or payload.get("device_id") or (payload.get("device") or {}).get("name")
    value: Any = payload.get("value")
    if value is None:
        data = payload.get("data") or {}
        value = data.get("temperature_c", data.get("value", data.get("state")))
        if et == "contact_opened":
            value = "open"
        if et == "contact_closed":
            value = "closed"
    ts = payload.get("timestamp") or payload.get("event_time") or (payload.get("meta") or {}).get("timestamp")
    return {"kind": kind, "device": device, "value": value, "ts": ts,
            "request_id": (payload.get("meta") or {}).get("request_id") or payload.get("request_id")}


def ingest(code: str, payload: dict[str, Any]) -> dict[str, Any]:
    n = normalise(payload)
    rid = n.get("request_id")
    if rid and not store.claim_request(code, rid):
        return {"duplicate": True, "kind": n["kind"]}
    store.add_signal(code, n["kind"], n["device"], n["value"], ts=n["ts"], raw=payload)
    return {"duplicate": False, "kind": n["kind"], "device": n["device"], "value": n["value"]}
