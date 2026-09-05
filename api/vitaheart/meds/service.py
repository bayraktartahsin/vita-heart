"""From a photo to a scheduled medicine, with every step attributable.

    photo (S3)  -> Reader (Nova Lite)      : what is printed
                -> Identifier (RxNorm)     : what it is, or "unconfirmed"
                -> Watchman (openFDA)      : live recalls, lot carried
                -> schedule.parse          : slots, never times
                -> DynamoDB MED#           : stored with sources and the trace

The agents package is importable from the Lambda because scripts/deploy.py ships
it next to this package. The AgentCore-hosted fleet (Phase 2.3) runs the same
functions; this module is the direct path the API uses for one photo.
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

# agents/ sits next to vitaheart/ in the deployed zip and two levels up in the repo.
for cand in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[3]):
    if (cand / "agents").is_dir() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

from . import schedule  # noqa: E402
from .. import store  # noqa: E402


def _trace(steps: list[dict], agent: str, tool: str, said: str, **extra) -> None:
    steps.append({"ts": store.now_iso(), "agent": agent, "tool": tool, "said": said, **extra})


def read_photo(code: str, image_bytes: bytes, fmt: str, *, photo_key: str | None = None) -> dict[str, Any]:
    """Reader here (one vision call), then the fleet: Identifier, Watchman, Scheduler.

    The fleet runs on Bedrock AgentCore when VITAHEART_AGENT_ARN is set; otherwise
    in-process. Either way the result is assembled from the tools' ledger, and
    every tool call is kept as the trace the television and the web page show.
    """
    from agents import client, reader

    steps: list[dict] = []
    readings = reader.read(image_bytes, fmt=fmt)
    _trace(steps, "Reader", "read_label", f"{len(readings)} box(es) read", readings=[r.to_dict() for r in readings],
           model="Amazon Nova Lite")
    fleet_out = client.read_boxes([r.to_dict() for r in readings], session_id=None)
    for st in fleet_out.get("trace", []):
        steps.append({"ts": store.now_iso(), "agent": st.get("agent"), "tool": st.get("tool"), "said": st.get("said", ""),
                      "input": st.get("input", {}), "ms": st.get("ms")})
    meds = fleet_out.get("meds", [])
    for m in meds:
        m["photo"] = photo_key
        m["added"] = store.now_iso()
        m["trace"] = steps
        m["said"] = fleet_out.get("said", {})
        m["ran_on"] = fleet_out.get("ran_on")
        store.put_med(code, m)
    return {"meds": meds, "trace": steps, "said": fleet_out.get("said", {}), "ran_on": fleet_out.get("ran_on")}


def clock_from_profile(profile: dict[str, Any]) -> schedule.HouseholdClock:
    times = {}
    for slot, hhmm in (profile.get("clock") or {}).items():
        h, m = str(hhmm).split(":")
        times[slot] = time(int(h), int(m))
    return schedule.HouseholdClock(times=times, tz_offset_hours=int(profile.get("tz_offset_hours", 0)))


def due_doses(code: str, profile: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
    """What the board shows under Today: due now, with confirmation state."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)  # schedule works in naive UTC
    clock = clock_from_profile(profile)
    day = clock.local_date(now)
    confirmed = store.doses_confirmed(code, day.isoformat())
    out = []
    for m in store.list_meds(code):
        dirs = m.get("directions") or {}
        d = schedule.Directions(slots=tuple(dirs.get("slots") or ()), food=dirs.get("food"), understood=dirs.get("understood", False))
        for dose in schedule.doses_for_day(m["id"], d, clock, day):
            due = dose.due is not None and dose in schedule.due_now([dose], now)
            unscheduled = dose.due is None
            if due or unscheduled:
                out.append({"id": dose.id, "medId": m["id"], "name": m.get("name"), "strength": m.get("strength"),
                            "slot": dose.slot, "food": dose.food, "photo": m.get("photo"),
                            "dueAt": dose.due.isoformat(timespec="minutes") if dose.due else None,
                            "unscheduled": unscheduled, "confirmed": dose.id in confirmed,
                            "recallCount": len(m.get("recalls") or []), "status": m.get("status")})
    return out
