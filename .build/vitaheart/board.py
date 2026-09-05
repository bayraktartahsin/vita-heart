"""Build the Morning Board: what the television shows first.

Pure function over data already fetched, so it is testable without AWS.
The greeting is in the household's language; the rest is data, not prose.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

GREETINGS = {
    "tr": ("Günaydın", "İyi günler", "İyi akşamlar"),
    "en": ("Good morning", "Good afternoon", "Good evening"),
}


def greeting(lang: str, hour: int) -> str:
    morning, afternoon, evening = GREETINGS.get(lang, GREETINGS["en"])
    if hour < 12:
        return morning
    if hour < 18:
        return afternoon
    return evening


def build(profile: dict[str, Any], *, latest_message: dict[str, Any] | None,
          checked_in: bool, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    lang = profile.get("lang", "en")
    tz_offset = int(profile.get("tz_offset_hours", 0))
    local_hour = (now.hour + tz_offset) % 24
    return {
        "household": profile["code"],
        "greeting": f"{greeting(lang, local_hour)}, {profile['name']}",
        "person": {"name": profile["name"], "age": profile.get("age")},
        "family": profile.get("family", []),
        "dueDoses": [],           # Phase 2
        "restingHeartRate": profile.get("resting_hr"),   # Phase 3 replaces with Watch data
        "message": (
            {"author": latest_message["author"], "text": latest_message["text"], "ts": latest_message["ts"]}
            if latest_message else None
        ),
        "checkedInToday": checked_in,
        "localHour": local_hour,
        "generatedAt": now.isoformat(timespec="seconds"),
    }
