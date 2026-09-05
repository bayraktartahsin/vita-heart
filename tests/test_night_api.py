from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def test_night_run_writes_a_summary_without_the_model(ddb, monkeypatch):
    from vitaheart import store
    c = client(ddb)
    store.add_signal("AHMET1", "contact.open", "front door", None, ts="2026-09-05T00:10:00+00:00")
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
