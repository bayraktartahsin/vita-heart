"""DynamoDB access. One table, keyed by household.

    PK = HH#<code>          SK = PROFILE
                            SK = MSG#<ts>#<id>        family message
                            SK = CHECKIN#<date>       "I'm up" for the day
                            SK = EV#<ts>#<id>         event for the TV's live channel
                            SK = MED#<id>             a medicine (Phase 2)
                            SK = DOSE#<date>#<id>     a confirmed dose (Phase 2)

Every mutation that the television should notice also writes an EV# row; the
long-poll in api.app reads only EV# rows newer than the client's cursor.
Timestamps are ISO-8601 UTC with microseconds so they sort as strings.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from . import config

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name=config.REGION).Table(config.TABLE)
    return _table


def reset_for_tests() -> None:
    global _table
    _table = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _hh(code: str) -> str:
    return f"HH#{code.upper()}"


def storable(value: Any) -> Any:
    """DynamoDB refuses Python floats; store them as Decimal (and walk nested data)."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: storable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [storable(v) for v in value]
    return value




# ---- profile -----------------------------------------------------------------

def plain(value: Any) -> Any:
    """DynamoDB hands numbers back as Decimal; the API speaks JSON numbers."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value


def put_profile(code: str, profile: dict[str, Any]) -> None:
    table().put_item(Item={"PK": _hh(code), "SK": "PROFILE", **profile, "updated": now_iso()})


def get_profile(code: str) -> dict[str, Any] | None:
    r = table().get_item(Key={"PK": _hh(code), "SK": "PROFILE"})
    return plain(r.get("Item"))


# ---- events (the live channel) --------------------------------------------------

def emit(code: str, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    ts = now_iso()
    item = {"PK": _hh(code), "SK": f"EV#{ts}#{uuid.uuid4().hex[:8]}", "ts": ts,
            "kind": kind, "data": storable(data or {})}
    table().put_item(Item=item)
    return item


def events_since(code: str, since: str | None, limit: int = 50) -> list[dict[str, Any]]:
    cond = Key("PK").eq(_hh(code))
    if since:
        cond = cond & Key("SK").between(f"EV#{since}#￿", "EV#￿")
    else:
        cond = cond & Key("SK").begins_with("EV#")
    r = table().query(KeyConditionExpression=cond, Limit=limit)
    items = plain(r.get("Items", []))
    # `between` is inclusive at the low end; drop anything at or before the cursor.
    return [i for i in items if not since or i["ts"] > since]


# ---- family messages -----------------------------------------------------------

def post_message(code: str, author: str, text: str) -> dict[str, Any]:
    ts = now_iso()
    item = {"PK": _hh(code), "SK": f"MSG#{ts}#{uuid.uuid4().hex[:8]}", "ts": ts,
            "author": author, "text": text}
    table().put_item(Item=item)
    emit(code, "message", {"author": author, "text": text, "ts": ts})
    return item


def latest_message(code: str) -> dict[str, Any] | None:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("MSG#"),
                      ScanIndexForward=False, Limit=1)
    items = r.get("Items", [])
    return items[0] if items else None


def list_messages(code: str, limit: int = 20) -> list[dict[str, Any]]:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("MSG#"),
                      ScanIndexForward=False, Limit=limit)
    return r.get("Items", [])


# ---- check-in ------------------------------------------------------------------

def checkin(code: str, by: str = "tv") -> dict[str, Any]:
    ts = now_iso()
    item = {"PK": _hh(code), "SK": f"CHECKIN#{today()}", "ts": ts, "by": by}
    table().put_item(Item=item)
    emit(code, "checkin", {"ts": ts, "by": by})
    return item


def checkin_today(code: str) -> dict[str, Any] | None:
    r = table().get_item(Key={"PK": _hh(code), "SK": f"CHECKIN#{today()}"})
    return r.get("Item")


# ---- medicines and doses (Phase 2) -----------------------------------------------

def put_med(code: str, med: dict[str, Any]) -> dict[str, Any]:
    item = {"PK": _hh(code), "SK": f"MED#{med['id']}", **med, "updated": now_iso()}
    table().put_item(Item=item)
    emit(code, "med", {"id": med["id"], "name": med.get("name")})
    return item


def list_meds(code: str) -> list[dict[str, Any]]:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("MED#"))
    return [plain(i) for i in r.get("Items", [])]


def confirm_dose(code: str, dose_id: str, by: str = "tv") -> dict[str, Any]:
    ts = now_iso()
    item = {"PK": _hh(code), "SK": f"DOSE#{dose_id}", "ts": ts, "by": by}
    table().put_item(Item=item)
    emit(code, "dose", {"id": dose_id, "ts": ts, "by": by})
    return item


def doses_confirmed(code: str, day: str) -> set[str]:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with(f"DOSE#{day}#"))
    return {i["SK"][len("DOSE#"):] for i in r.get("Items", [])}


def set_clock(code: str, times: dict[str, str]) -> None:
    table().update_item(Key={"PK": _hh(code), "SK": "PROFILE"},
                        UpdateExpression="SET clock = :c, updated = :u",
                        ExpressionAttributeValues={":c": times, ":u": now_iso()})
    emit(code, "board", {"clock": times})


# ---- heart sessions (Phase 3) -------------------------------------------------------

def start_session(code: str, session_id: str, source: str) -> dict[str, Any]:
    ts = now_iso()
    item = {"PK": _hh(code), "SK": f"SESSION#{session_id}", "id": session_id, "started": ts, "source": source, "state": "live"}
    table().put_item(Item=item)
    emit(code, "session", {"id": session_id, "state": "live", "source": source})
    return item


def add_hr(code: str, session_id: str, bpm: int, at: str | None = None) -> dict[str, Any]:
    ts = at or now_iso()
    item = {"PK": _hh(code), "SK": f"HR#{session_id}#{ts}", "ts": ts, "bpm": int(bpm), "session": session_id,
            "ttl": int(datetime.now(timezone.utc).timestamp()) + 7 * 86400}
    table().put_item(Item=item)
    emit(code, "hr", {"session": session_id, "bpm": int(bpm), "ts": ts})
    return item


def finish_session(code: str, session_id: str, summary: dict[str, Any]) -> None:
    table().update_item(Key={"PK": _hh(code), "SK": f"SESSION#{session_id}"},
                        UpdateExpression="SET #s = :s, summary = :m, finished = :f",
                        ExpressionAttributeNames={"#s": "state"},
                        ExpressionAttributeValues={":s": "finished", ":m": storable(summary), ":f": now_iso()})
    emit(code, "session", {"id": session_id, "state": "finished", "summary": summary})


def live_session(code: str) -> dict[str, Any] | None:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("SESSION#"),
                      ScanIndexForward=False, Limit=5)
    for i in r.get("Items", []):
        if i.get("state") == "live":
            return plain(i)
    return None


# ---- Ring signals, summaries, trace (Phase 4) ------------------------------------

def add_signal(code: str, kind: str, device: str | None, value: Any, ts: str | None = None, raw: dict | None = None) -> dict[str, Any]:
    ts = ts or now_iso()
    item = {"PK": _hh(code), "SK": f"SIGNAL#{ts}#{uuid.uuid4().hex[:6]}", "ts": ts, "kind": kind, "device": device or "",
            "value": storable(value) if value is not None else "", "raw": storable(raw or {}),
            "ttl": int(datetime.now(timezone.utc).timestamp()) + 14 * 86400}
    table().put_item(Item=item)
    emit(code, "signal", {"kind": kind, "device": device, "value": value, "ts": ts})
    return item


def signals_since(code: str, since_iso: str) -> list[dict[str, Any]]:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").between(f"SIGNAL#{since_iso}", "SIGNAL#￿"))
    return plain(r.get("Items", []))


def put_summary(code: str, day: str, text: str, signals: list[dict[str, Any]]) -> dict[str, Any]:
    item = {"PK": _hh(code), "SK": f"SUMMARY#{day}", "day": day, "text": text, "signals": storable(signals), "ts": now_iso()}
    table().put_item(Item=item)
    emit(code, "summary", {"day": day, "text": text})
    return item


def latest_summary(code: str) -> dict[str, Any] | None:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("SUMMARY#"),
                      ScanIndexForward=False, Limit=1)
    items = r.get("Items", [])
    return plain(items[0]) if items else None


def sessions_since(code: str, since_iso: str) -> list[dict[str, Any]]:
    r = table().query(KeyConditionExpression=Key("PK").eq(_hh(code)) & Key("SK").begins_with("SESSION#"))
    return [plain(i) for i in r.get("Items", []) if i.get("started", "") >= since_iso]


def list_households() -> list[str]:
    r = table().scan(FilterExpression=Key("SK").eq("PROFILE"), ProjectionExpression="PK")
    return [i["PK"].split("#", 1)[1] for i in r.get("Items", [])]
