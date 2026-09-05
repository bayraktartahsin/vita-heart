"""Turn a label's dosing words into household times, without guessing.

The VitaCircle rule: a pharmacy label says "twice daily"; it does not say 09:00.
Every app silently decides 09:00. Here, frequency words become *slots* (morning,
midday, evening, night) and the household maps slots to its own clock once, on
the television. Until a slot is mapped, the dose is "unscheduled", and the board
says so instead of inventing a time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

SLOTS = ("morning", "midday", "evening", "night")

# Household defaults are only proposals; the TV asks the person to confirm them once.
PROPOSED_TIMES = {"morning": time(8, 0), "midday": time(13, 0), "evening": time(19, 0), "night": time(22, 0)}

_PATTERNS: list[tuple[re.Pattern[str], tuple[str, ...]]] = [
    # Most specific first: a phrase like "sabah ve akşam" must win over the bare "sabah".
    (re.compile(r"\b(four times|4x|4 times)\b.*\b(daily|a day|per day)\b|\bqid\b|\bgünde 4\b|\bgünde dört\b", re.I), ("morning", "midday", "evening", "night")),
    (re.compile(r"\b(three times|thrice|3x|3 times)\b.*\b(daily|a day|per day)\b|\btid\b|\bgünde 3\b|\bgünde üç\b", re.I), ("morning", "midday", "evening")),
    (re.compile(r"\b(twice|two times|2x|2 times)\b.*\b(daily|a day|per day)\b|\bbid\b|\bgünde 2\b|\bgünde iki\b|\bsabah\s*(ve|-|,)\s*akşam\b", re.I), ("morning", "evening")),
    (re.compile(r"\bat night\b|\bbefore bed\b|\bbedtime\b|\bnightly\b|\bgece\b|\byatmadan\b", re.I), ("night",)),
    (re.compile(r"\bevery evening\b|\bin the evening\b|\bakşam\b", re.I), ("evening",)),
    (re.compile(r"\bwith lunch\b|\bmidday\b|\böğle\b", re.I), ("midday",)),
    (re.compile(r"\b(once|one time|1x|1 time)\b.*\b(daily|a day|per day)\b|\bonce daily\b|\bevery morning\b|\bsabah\b|\bgünde 1\b|\bgünde bir\b", re.I), ("morning",)),
]

_FOOD = [
    (re.compile(r"\bwith food\b|\bwith meals?\b|\bafter (a )?meals?\b|\btok\b|\byemekten sonra\b|\byemekle\b", re.I), "with food"),
    (re.compile(r"\bempty stomach\b|\bbefore (a )?meals?\b|\baç\b|\byemekten önce\b", re.I), "before food"),
]


@dataclass
class Directions:
    slots: tuple[str, ...]            # empty when the words were not understood
    food: str | None = None
    source_text: str = ""
    understood: bool = True

    @property
    def per_day(self) -> int:
        return len(self.slots)


def parse(text: str) -> Directions:
    """Read dosing words. Unknown words produce `understood=False`, never a guess."""
    t = " ".join((text or "").split())
    food = next((label for pat, label in _FOOD if pat.search(t)), None)
    for pat, slots in _PATTERNS:
        if pat.search(t):
            return Directions(slots=slots, food=food, source_text=t)
    return Directions(slots=(), food=food, source_text=t, understood=False)


@dataclass
class Dose:
    med_id: str
    slot: str
    due: datetime | None          # None until the household mapped the slot
    date: date
    food: str | None = None

    @property
    def id(self) -> str:
        return f"{self.date.isoformat()}#{self.slot}#{self.med_id}"


@dataclass
class HouseholdClock:
    """The household's own mapping from slot to local time. Confirmed on the TV."""
    times: dict[str, time] = field(default_factory=dict)
    tz_offset_hours: int = 0

    def local_date(self, now_utc: datetime) -> date:
        return (now_utc + timedelta(hours=self.tz_offset_hours)).date()

    def due_utc(self, day: date, slot: str) -> datetime | None:
        t = self.times.get(slot)
        if t is None:
            return None
        local = datetime.combine(day, t)
        return local - timedelta(hours=self.tz_offset_hours)


def doses_for_day(med_id: str, directions: Directions, clock: HouseholdClock, day: date) -> list[Dose]:
    return [Dose(med_id=med_id, slot=s, due=clock.due_utc(day, s), date=day, food=directions.food) for s in directions.slots]


def due_now(doses: list[Dose], now_utc: datetime, window_before_min: int = 30, window_after_min: int = 120) -> list[Dose]:
    """A dose is 'due' from 30 minutes before its time until two hours after."""
    out = []
    for d in doses:
        if d.due is None:
            continue
        if d.due - timedelta(minutes=window_before_min) <= now_utc <= d.due + timedelta(minutes=window_after_min):
            out.append(d)
    return out
