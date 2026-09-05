from datetime import datetime, timezone

from vitaheart import board


PROFILE = {"code": "AHMET1", "name": "Ahmet", "age": 72, "lang": "tr", "tz_offset_hours": 3,
           "family": [{"name": "Selin"}]}


def test_greeting_follows_local_hour_and_language():
    at_0540_utc = datetime(2026, 9, 5, 5, 40, tzinfo=timezone.utc)   # 08:40 Istanbul
    b = board.build(PROFILE, latest_message=None, checked_in=False, now=at_0540_utc)
    assert b["greeting"] == "Günaydın, Ahmet"
    assert b["localHour"] == 8
    at_1600_utc = datetime(2026, 9, 5, 16, 0, tzinfo=timezone.utc)   # 19:00 Istanbul
    assert board.build(PROFILE, latest_message=None, checked_in=False, now=at_1600_utc)["greeting"].startswith("İyi akşamlar")


def test_english_fallback_for_unknown_language():
    p = {**PROFILE, "lang": "xx", "tz_offset_hours": 0}
    b = board.build(p, latest_message=None, checked_in=True, now=datetime(2026, 9, 5, 13, 0, tzinfo=timezone.utc))
    assert b["greeting"] == "Good afternoon, Ahmet"
    assert b["checkedInToday"] is True


def test_message_is_carried_verbatim():
    msg = {"author": "Selin", "text": "Baba, akşam arayacağım.", "ts": "2026-09-05T05:00:00+00:00"}
    b = board.build(PROFILE, latest_message=msg, checked_in=False)
    assert b["message"] == msg
    assert b["dueDoses"] == []
