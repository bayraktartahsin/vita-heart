from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def test_session_lifecycle_and_hr_on_the_events_channel(ddb):
    c = client(ddb)
    assert c.get("/session/live", params={"household": "AHMET1"}).json()["live"] is None
    sid = c.post("/session/start", json={"household": "AHMET1", "source": "watch"}).json()["id"]
    assert c.get("/session/live", params={"household": "AHMET1"}).json()["live"]["id"] == sid
    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    assert c.post("/session/hr", json={"household": "AHMET1", "session": sid, "bpm": 84}).status_code == 202
    ev = c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"]
    assert ev[-1]["kind"] == "hr" and ev[-1]["data"]["bpm"] == 84
    r = c.post("/session/finish", json={"household": "AHMET1", "session": sid, "summary": {"minutesActive": 10}})
    assert r.status_code == 200
    assert c.get("/session/live", params={"household": "AHMET1"}).json()["live"] is None


def test_hr_for_a_session_that_is_not_live_is_refused(ddb):
    c = client(ddb)
    assert c.post("/session/hr", json={"household": "AHMET1", "session": "nope123", "bpm": 80}).status_code == 409


def test_hr_out_of_range_is_rejected(ddb):
    c = client(ddb)
    sid = c.post("/session/start", json={"household": "AHMET1"}).json()["id"]
    assert c.post("/session/hr", json={"household": "AHMET1", "session": sid, "bpm": 300}).status_code == 422
