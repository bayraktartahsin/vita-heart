"""The Night Watch rules. Pure functions over the day's facts.

Inputs are plain dicts the store already holds: Ring signals (door, motion,
temperature, air, device state), doses confirmed, the morning check-in, and the
heart session. Outputs are `Signal`s: a kind, a calm one-line note, and the
evidence. No rule uses the words alarm, monitor, detect or diagnose. A signal is
something for a daughter to know about, not something to act on tonight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

QUIET_START = time(23, 0)
QUIET_END = time(6, 0)
NO_MOTION_BY = time(10, 0)
COLD_C = 18.0
COLD_MIN_HOURS = 2.0
OFFLINE_HOURS = 24.0


@dataclass
class Signal:
    kind: str
    note: str
    evidence: dict[str, Any] = field(default_factory=dict)
    weight: int = 1          # 1 worth a mention, 2 worth a sentence of its own


def _local(ts: str, tz_offset_hours: int) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (dt.replace(tzinfo=None) + timedelta(hours=tz_offset_hours))


def _in_quiet_hours(t: time) -> bool:
    return t >= QUIET_START or t < QUIET_END


def door_at_night(events: list[dict[str, Any]], tz: int) -> list[Signal]:
    out = []
    for e in events:
        if e.get("kind") in ("contact.open", "doorbell.press"):
            t = _local(e["ts"], tz)
            if _in_quiet_hours(t.time()):
                what = "the front door opened" if e["kind"] == "contact.open" else "the doorbell rang"
                out.append(Signal("door-at-night", f"At {t:%H:%M} {what}.", {"ts": e["ts"], "device": e.get("device")}, weight=2))
    return out


def no_motion_by_morning(events: list[dict[str, Any]], now_local: datetime, checked_in: bool, tz: int) -> list[Signal]:
    """After 10:00 local, with no check-in and nothing moving since local midnight."""
    if checked_in or now_local.time() < NO_MOTION_BY:
        return []
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    moved_today = any(e.get("kind") in ("motion", "contact.open", "contact.close", "doorbell.press")
                      and day_start <= _local(e["ts"], tz) <= now_local for e in events)
    if moved_today:
        return []
    return [Signal("quiet-morning", f"No movement had been noticed by {NO_MOTION_BY:%H:%M} and the morning board was not answered.", {}, weight=2)]


def cold_indoors(readings: list[dict[str, Any]], tz: int) -> list[Signal]:
    """Two hours or more of readings under 18 C from the same sensor."""
    by_device: dict[str, list[tuple[datetime, float]]] = {}
    for r in readings:
        if r.get("kind") == "temperature" and r.get("value") is not None:
            by_device.setdefault(r.get("device", "?"), []).append((_local(r["ts"], tz), float(r["value"])))
    out = []
    for dev, pts in by_device.items():
        pts.sort()
        run_start = None
        for t, v in pts:
            if v < COLD_C:
                run_start = run_start or t
                if (t - run_start) >= timedelta(hours=COLD_MIN_HOURS):
                    out.append(Signal("cold-indoors", f"The hall has been under {int(COLD_C)} degrees since {run_start:%H:%M} (down to {v:.0f}).", {"device": dev, "since": run_start.isoformat()}, weight=1))
                    break
            else:
                run_start = None
    return out


def air_quality(readings: list[dict[str, Any]], tz: int) -> list[Signal]:
    out = []
    for r in readings:
        if r.get("kind") == "air.alert":
            t = _local(r["ts"], tz)
            out.append(Signal("air", f"The air quality sensor raised a notice at {t:%H:%M} ({r.get('value', 'no detail')}).", {"device": r.get("device")}, weight=1))
    return out


def device_offline(events: list[dict[str, Any]], now_local: datetime, tz: int) -> list[Signal]:
    last_state: dict[str, tuple[datetime, str]] = {}
    for e in sorted(events, key=lambda x: x["ts"]):
        if e.get("kind") in ("device.online", "device.offline"):
            last_state[e.get("device", "?")] = (_local(e["ts"], tz), e["kind"])
    out = []
    for dev, (t, kind) in last_state.items():
        if kind == "device.offline" and now_local - t >= timedelta(hours=OFFLINE_HOURS):
            out.append(Signal("device-offline", f"The {dev} has been offline since {t:%a %H:%M}.", {"device": dev}, weight=1))
    return out


def doses(due: list[dict[str, Any]]) -> list[Signal]:
    scheduled = [d for d in due if not d.get("unscheduled")]
    unscheduled = [d for d in due if d.get("unscheduled")]
    taken = [d for d in scheduled if d.get("confirmed")]
    missed = [d for d in scheduled if not d.get("confirmed")]
    out = []
    if scheduled:
        out.append(Signal("doses", f"{len(taken)} of {len(scheduled)} scheduled doses were confirmed on the television.",
                          {"missed": [f"{d.get('name')} ({d.get('slot')})" for d in missed]}, weight=2 if missed else 1))
    elif unscheduled:
        out.append(Signal("doses", "Medicines are on the television but their times have not been set yet.", {}, weight=1))
    return out


def session(summary: dict[str, Any] | None) -> list[Signal]:
    if not summary:
        return [Signal("session", "No seated session today.", {}, weight=1)]
    mins = summary.get("minutesActive")
    share = summary.get("inRangeShare")
    txt = f"A seated session of {mins} minutes"
    if share is not None:
        txt += f", heart rate in the gentle range {int(float(share) * 100)}% of the time"
    txt += "."
    return [Signal("session", txt, summary, weight=1)]


def evaluate(*, ring_events: list[dict[str, Any]], due_doses: list[dict[str, Any]], session_summary: dict[str, Any] | None,
             checked_in: bool, now_utc: datetime, tz_offset_hours: int) -> list[Signal]:
    now_local = now_utc.replace(tzinfo=None) + timedelta(hours=tz_offset_hours)
    signals: list[Signal] = []
    signals += door_at_night(ring_events, tz_offset_hours)
    signals += no_motion_by_morning(ring_events, now_local, checked_in, tz_offset_hours)
    signals += cold_indoors(ring_events, tz_offset_hours)
    signals += air_quality(ring_events, tz_offset_hours)
    signals += device_offline(ring_events, now_local, tz_offset_hours)
    signals += doses(due_doses)
    signals += session(session_summary)
    banned = ("alarm", "monitor", "detect", "diagnos")
    for s in signals:
        if any(b in s.note.lower() for b in banned):   # a device name could smuggle one in; rewrite rather than raise
            s.note = s.note.replace("monitor", "sensor").replace("Monitor", "Sensor")
    return signals
