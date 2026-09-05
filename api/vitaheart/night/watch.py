"""The nightly pass: facts in, one calm paragraph out, delivered to the family.

Runs from EventBridge at 21:00 local (18:00 UTC for Istanbul) through the Lambda
handler, and on demand from POST /night/run for the demo. The Scribe agent on
AgentCore writes the sentence from the signals; if the model is unavailable the
signals' own notes are joined, so the family always gets something true.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .. import store
from ..meds import service as meds
from . import rules

for cand in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[3]):
    if (cand / "agents").is_dir() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))


def facts_for(code: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    profile = store.get_profile(code) or {}
    since = (now - timedelta(hours=24)).isoformat(timespec="microseconds")
    ring_events = [{"kind": s["kind"], "ts": s["ts"], "device": s.get("device"), "value": s.get("value")}
                   for s in store.signals_since(code, since)]
    sessions = [s for s in store.sessions_since(code, since) if s.get("summary")]
    return {
        "profile": profile,
        "ring_events": ring_events,
        "due_doses": meds.due_doses(code, profile, now) if profile else [],
        "session_summary": sessions[-1]["summary"] if sessions else None,
        "checked_in": store.checkin_today(code) is not None,
        "now": now,
    }


def run_for(code: str, now: datetime | None = None, notify: bool = True) -> dict[str, Any]:
    f = facts_for(code, now)
    profile = f["profile"]
    signals = rules.evaluate(ring_events=f["ring_events"], due_doses=f["due_doses"], session_summary=f["session_summary"],
                             checked_in=f["checked_in"], now_utc=f["now"], tz_offset_hours=int(profile.get("tz_offset_hours", 0)))
    sig_dicts = [{"kind": s.kind, "note": s.note, "weight": s.weight} for s in signals]
    daughter = (profile.get("family") or [{}])[0].get("name", "the family")
    text = ""
    try:
        from agents import client
        text = client.family_line({"person": profile.get("name"), "for": daughter, "signals": [s.note for s in signals]})
    except Exception:  # noqa: BLE001
        text = ""
    if not text:
        text = " ".join(s.note for s in signals) or f"A quiet day for {profile.get('name', 'him')}."
    day = (f["now"] + timedelta(hours=int(profile.get("tz_offset_hours", 0)))).date().isoformat()
    store.put_summary(code, day, text, sig_dicts)
    delivered = False
    if notify:
        delivered = _email(code, profile, text, sig_dicts)
    return {"day": day, "text": text, "signals": sig_dicts, "delivered": delivered}


def _email(code: str, profile: dict, text: str, signals: list[dict]) -> bool:
    topic = os.environ.get("VITAHEART_TOPIC_ARN")
    if not topic:
        return False
    import boto3

    body = f"{text}\n\n" + "\n".join(f"- {s['note']}" for s in signals) + \
        f"\n\nReply from your phone: {os.environ.get('VITAHEART_PUBLIC_URL', '')}/family?household={code}\n"
    boto3.client("sns", region_name=os.environ.get("VITAHEART_REGION", "eu-north-1")).publish(
        TopicArn=topic, Subject=f"Vita Heart · {profile.get('name', code)} today", Message=body)
    return True


def run_all(now: datetime | None = None) -> list[dict[str, Any]]:
    return [{"household": code, **run_for(code, now)} for code in store.list_households()]
