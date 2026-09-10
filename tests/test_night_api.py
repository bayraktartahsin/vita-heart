from datetime import datetime, timezone

from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def test_night_run_writes_a_summary_without_the_model(ddb, monkeypatch):
    from vitaheart import store
    c = client(ddb)
    # 00:10 UTC today = 03:10 in Istanbul: inside quiet hours and inside the 24-hour window,
    # whenever the suite happens to run. A fixed date silently ages out of the window.
    at = datetime.now(timezone.utc).replace(hour=0, minute=10, second=0, microsecond=0)
    store.add_signal("AHMET1", "contact.open", "front door", None, ts=at.isoformat())
    c.post("/checkin", json={"household": "AHMET1"})
    # No AgentCore, no model: the summary is the signals' own notes.
    import agents.client as ac
    monkeypatch.setattr(ac, "family_line", lambda facts: (_ for _ in ()).throw(RuntimeError("offline")))
    out = c.post("/night/run", json={"household": "AHMET1", "notify": False}).json()
    assert "the front door opened" in out["text"]
    assert out["delivered"] is False
    s = c.get("/family/summary", params={"household": "AHMET1"}).json()["summary"]
    assert s["text"] == out["text"] and s["signals"][0]["kind"] == "door-at-night"


def test_family_page_and_trace_routes(ddb):
    c = client(ddb)
    assert "Vita Heart" in c.get("/family").text
    assert c.get("/trace", params={"household": "AHMET1"}).json() == {"steps": []}


def test_an_abandoned_session_is_not_reported_as_a_seated_session(ddb):
    """Reset cuts a session short but leaves the summary it had.

    Tonight's page then told the family he had done a seated session that had been
    thrown away — beside a panel that said the day had not started.
    """
    c = client(ddb)
    sid = c.post("/session/start", json={"household": "AHMET1", "source": "recorded"}).json()["id"]
    c.post("/session/hr", json={"household": "AHMET1", "session": sid, "bpm": 88})
    c.post("/session/finish", json={"household": "AHMET1", "session": sid,
                                    "summary": {"minutesActive": 3.0, "inRangeShare": 0.8}})
    after_finished = c.post("/night/run", json={"household": "AHMET1", "notify": False}).json()
    assert "seated session" in after_finished["text"]
    assert "No seated session" not in after_finished["text"]

    c.post("/demo/reset", json={"household": "AHMET1"})
    text = c.get("/family/summary", params={"household": "AHMET1"}).json()["summary"]["text"]
    assert "No seated session today" in text, text
