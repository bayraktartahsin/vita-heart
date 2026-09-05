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
import uuid
from dataclasses import asdict
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
    from agents import names, reader
    from agents.vendored import fda, rxnorm

    steps: list[dict] = []
    readings = reader.read(image_bytes, fmt=fmt)
    _trace(steps, "Reader", "read_label", f"{len(readings)} box(es) read", readings=[r.to_dict() for r in readings])

    meds: list[dict[str, Any]] = []
    for r in readings:
        med: dict[str, Any] = {"id": uuid.uuid4().hex[:10], "photo": photo_key, "printed": r.to_dict(),
                               "name": r.name, "strength": r.strength, "form": r.form,
                               "identity": None, "recalls": [], "directions": None, "added": store.now_iso()}
        if not r.legible or not r.name:
            med["status"] = "unreadable"
            _trace(steps, "Reader", "read_label", "a box could not be read; nothing was guessed")
            meds.append(med)
            continue
        inn = names.to_inn(r.name)
        query = " ".join(x for x in ((inn or r.name), r.strength) if x)
        if inn:
            _trace(steps, "Identifier", "map_name", f"{r.name} is sold internationally as {inn}", source="agents/names.py")
        try:
            drug = rxnorm.identify(query)
            identity = asdict(drug) if hasattr(drug, "__dataclass_fields__") else dict(drug.__dict__)
            if identity.get("rxcui"):
                med["identity"] = identity
                med["status"] = "identified"
                _trace(steps, "Identifier", "identify_medicine", f"{r.name} confirmed as {identity.get('name')}", rxcui=identity["rxcui"], source="RxNorm (NIH)")
            else:
                med["status"] = "unconfirmed"
                _trace(steps, "Identifier", "identify_medicine", f"{r.name} is not in RxNorm under that name; stored as unconfirmed", source="RxNorm (NIH)")
        except Exception as e:  # RxNorm unavailable
            med["status"] = "unconfirmed"
            _trace(steps, "Identifier", "identify_medicine", f"RxNorm unavailable ({type(e).__name__}); {r.name} stored as unconfirmed")
        ingredients = (med.get("identity") or {}).get("ingredients") or []
        ingredient = ingredients[0][1] if ingredients else (inn or r.name)
        try:
            recs = fda.recalls(ingredient, live_only=True)
            med["recalls"] = [asdict(x) if hasattr(x, "__dataclass_fields__") else dict(x.__dict__) for x in recs][:5]
            _trace(steps, "Watchman", "check_for_recalls", f"{len(recs)} live recall(s) for {ingredient}")
        except Exception as e:
            _trace(steps, "Watchman", "check_for_recalls", f"safety record unavailable ({type(e).__name__}); nothing assumed")
        d = schedule.parse(r.directions or "")
        med["directions"] = {"slots": list(d.slots), "food": d.food, "understood": d.understood, "text": d.source_text}
        _trace(steps, "Scheduler", "parse_directions",
               f"{'/'.join(d.slots) if d.slots else 'directions not understood, the television will ask'}")
        meds.append(med)

    for m in meds:
        m["trace"] = steps
        store.put_med(code, m)
    return {"meds": meds, "trace": steps}


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
