from datetime import date, datetime, time, timezone

from vitaheart.meds import schedule as s


def test_twice_daily_becomes_two_slots_not_two_times():
    d = s.parse("Take one tablet twice daily with food")
    assert d.slots == ("morning", "evening") and d.food == "with food" and d.understood


def test_turkish_directions_are_understood():
    assert s.parse("Günde 2 kez, yemekten sonra").slots == ("morning", "evening")
    assert s.parse("Sabah ve akşam birer tablet").slots == ("morning", "evening")
    assert s.parse("Yatmadan önce 1 tablet").slots == ("night",)


def test_unknown_words_are_not_guessed():
    d = s.parse("As directed by your physician")
    assert d.slots == () and d.understood is False


def test_dose_time_is_none_until_the_household_maps_the_slot():
    clock = s.HouseholdClock(times={"morning": time(8, 0)}, tz_offset_hours=3)
    doses = s.doses_for_day("m1", s.parse("twice daily"), clock, date(2026, 9, 5))
    by_slot = {d.slot: d for d in doses}
    assert by_slot["morning"].due == datetime(2026, 9, 5, 5, 0)      # 08:00 Istanbul in UTC
    assert by_slot["evening"].due is None


def test_due_window():
    clock = s.HouseholdClock(times={"morning": time(8, 0)}, tz_offset_hours=3)
    doses = s.doses_for_day("m1", s.parse("once daily"), clock, date(2026, 9, 5))
    assert s.due_now(doses, datetime(2026, 9, 5, 4, 45)) != []      # 07:45, inside the 30 min before
    assert s.due_now(doses, datetime(2026, 9, 5, 7, 1)) == []       # 10:01, past the 2 h window
