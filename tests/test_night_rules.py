from datetime import datetime

from vitaheart.night import rules as R

TZ = 3  # Istanbul


def ev(kind, ts, device="front door", value=None):
    return {"kind": kind, "ts": ts, "device": device, "value": value}


def test_door_opening_at_three_in_the_morning_is_noted_calmly():
    sig = R.evaluate(ring_events=[ev("contact.open", "2026-09-05T00:10:00+00:00")], due_doses=[], session_summary=None,
                     checked_in=True, now_utc=datetime(2026, 9, 5, 18, 0), tz_offset_hours=TZ)
    door = [s for s in sig if s.kind == "door-at-night"]
    assert len(door) == 1 and door[0].note == "At 03:10 the front door opened."


def test_door_in_the_afternoon_is_not_a_signal():
    sig = R.evaluate(ring_events=[ev("contact.open", "2026-09-05T12:00:00+00:00")], due_doses=[], session_summary=None,
                     checked_in=True, now_utc=datetime(2026, 9, 5, 18, 0), tz_offset_hours=TZ)
    assert not [s for s in sig if s.kind == "door-at-night"]


def test_quiet_morning_only_when_nothing_moved_and_no_checkin():
    late_morning = datetime(2026, 9, 5, 7, 30)  # 10:30 Istanbul
    quiet = R.evaluate(ring_events=[], due_doses=[], session_summary=None, checked_in=False, now_utc=late_morning, tz_offset_hours=TZ)
    assert [s.kind for s in quiet if s.kind == "quiet-morning"] == ["quiet-morning"]
    moved = R.evaluate(ring_events=[ev("motion", "2026-09-05T05:40:00+00:00", "hall")], due_doses=[], session_summary=None,
                       checked_in=False, now_utc=late_morning, tz_offset_hours=TZ)
    assert not [s for s in moved if s.kind == "quiet-morning"]
    checked = R.evaluate(ring_events=[], due_doses=[], session_summary=None, checked_in=True, now_utc=late_morning, tz_offset_hours=TZ)
    assert not [s for s in checked if s.kind == "quiet-morning"]


def test_cold_indoors_needs_two_hours_under_eighteen():
    short = [ev("temperature", "2026-09-05T03:00:00+00:00", "hall", 16.5), ev("temperature", "2026-09-05T04:00:00+00:00", "hall", 16.0)]
    assert not R.cold_indoors(short, TZ)
    long = short + [ev("temperature", "2026-09-05T05:10:00+00:00", "hall", 16.2)]
    sig = R.cold_indoors(long, TZ)
    assert len(sig) == 1 and sig[0].note.startswith("The hall has been under 18 degrees since 06:00")


def test_doses_and_session_sentences():
    due = [{"name": "CORASPIN", "slot": "morning", "confirmed": True}, {"name": "Metformin", "slot": "evening", "confirmed": False}]
    sig = R.evaluate(ring_events=[], due_doses=due, session_summary={"minutesActive": 9.5, "inRangeShare": 0.8},
                     checked_in=True, now_utc=datetime(2026, 9, 5, 18, 0), tz_offset_hours=TZ)
    notes = {s.kind: s.note for s in sig}
    assert notes["doses"] == "1 of 2 scheduled doses were confirmed on the television."
    only_unscheduled = R.doses([{"name": "X", "slot": "morning", "unscheduled": True}])
    assert only_unscheduled[0].note.startswith("Medicines are on the television but their times")
    assert R.doses([]) == []
    assert notes["session"] == "A seated session of 9.5 minutes, heart rate in the gentle range 80% of the time."


def test_no_banned_words_ever():
    sig = R.evaluate(ring_events=[ev("device.offline", "2026-09-03T10:00:00+00:00", "hall camera"), ev("air.alert", "2026-09-05T09:00:00+00:00", "air quality monitor", "PM2.5 high")],
                     due_doses=[], session_summary=None, checked_in=True, now_utc=datetime(2026, 9, 5, 18, 0), tz_offset_hours=TZ)
    text = " ".join(s.note for s in sig).lower()
    for w in ("alarm", "monitor ", "detect", "diagnos"):
        assert w not in text
