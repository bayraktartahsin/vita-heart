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
