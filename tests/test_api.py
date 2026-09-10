from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def test_health(ddb):
    c = client(ddb)
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_board_for_seeded_household(ddb):
    c = client(ddb)
    r = c.get("/board", params={"household": "AHMET1"})
    assert r.status_code == 200
    b = r.json()
    assert b["person"]["name"] == "Ahmet"
    assert b["person"]["age"] == 72 and b["restingHeartRate"] == 61   # numbers, not Decimal strings
    assert b["message"]["author"] == "Selin"
    assert b["checkedInToday"] is False


def test_unknown_household_is_404(ddb):
    c = client(ddb)
    assert c.get("/board", params={"household": "NOBODY"}).status_code == 404


def test_long_poll_returns_new_events_and_cursor_advances(ddb):
    c = client(ddb)
    first = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()
    assert first["events"] == [] and first["cursor"]
    c.post("/family/messages", json={"household": "AHMET1", "author": "Selin", "text": "Merhaba"})
    c.post("/checkin", json={"household": "AHMET1", "by": "tv"})
    second = c.get("/events", params={"household": "AHMET1", "since": first["cursor"], "wait": 0}).json()
    kinds = [e["kind"] for e in second["events"]]
    assert kinds == ["message", "checkin"]
    assert second["cursor"] == second["events"][-1]["ts"]
    third = c.get("/events", params={"household": "AHMET1", "since": second["cursor"], "wait": 0}).json()
    assert third["events"] == []


def test_checkin_shows_on_board(ddb):
    c = client(ddb)
    c.post("/checkin", json={"household": "AHMET1"})
    assert c.get("/board", params={"household": "AHMET1"}).json()["checkedInToday"] is True


def test_a_cursor_whose_plus_became_a_space_does_not_replay_the_event(ddb):
    """The bug that answered one Alexa question eight times.

    A cursor is "…+00:00". Interpolated into a URL unencoded, the plus arrives as a
    space, the range bound falls under the last event, and every poll delivers it again.
    """
    c = client(ddb)
    start = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    c.post("/checkin", json={"household": "AHMET1"})
    first = c.get("/events", params={"household": "AHMET1", "since": start, "wait": 0}).json()
    assert first["events"], "expected the check-in on the channel"
    cursor = first["cursor"]
    assert "+" in cursor, "this test is meaningless if the cursor carries no offset"

    # exactly what an unencoded query string delivers
    mangled = cursor.replace("+", " ")
    again = c.get("/events", params={"household": "AHMET1", "since": mangled, "wait": 0}).json()
    assert again["events"] == [], f"the event was handed back again: {again['events']}"

    # and the honest cursor still behaves
    clean = c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()
    assert clean["events"] == []


def test_events_expire_so_the_channel_is_a_tail_not_an_archive(ddb):
    """Every event was being kept for ever, and the channel is only ever read seconds old."""
    import time as _time
    c = client(ddb)
    c.post("/checkin", json={"household": "AHMET1"})
    from vitaheart import store
    rows = store.table().query(
        KeyConditionExpression=__import__("boto3").dynamodb.conditions.Key("PK").eq("HH#AHMET1")
        & __import__("boto3").dynamodb.conditions.Key("SK").begins_with("EV#"))["Items"]
    assert rows, "expected an event"
    for r in rows:
        assert "ttl" in r, "an event with no ttl never leaves the table"
        assert 0 < int(r["ttl"]) - int(_time.time()) <= 3 * 86400 + 60
