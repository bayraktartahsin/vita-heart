from fastapi.testclient import TestClient


def test_turn_requires_a_token(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    c = TestClient(appmod.app)
    assert c.post("/alexa-sim/turn", json={"utterance": "hi"}).status_code == 401
    assert "Alexa+" in c.get("/alexa-sim").text


def test_tool_call_helper_handles_both_result_shapes(ddb, monkeypatch):
    import asyncio
    from alexa import server as srv, sim
    from vitaheart import seed
    seed.main()
    fm = srv.build_server()
    tok = srv.current_household.set("AHMET1")
    try:
        out = sim._call(fm, "get_family_status", {})
    finally:
        srv.current_household.reset(tok)
    assert out["checkedInToday"] is False


def test_a_turn_is_announced_on_the_household_channel(ddb, monkeypatch):
    """Otherwise nothing outside that one browser tab can tell whether Alexa answered."""
    from vitaheart import seed, app as app_mod
    from alexa import sim
    seed.main()

    monkeypatch.setattr(sim, "turn", lambda hh, utt: {"speech": "He is fine.", "tool": "get_family_status", "ms": 120})
    monkeypatch.setattr(app_mod._oauth, "household_for", lambda tok: "AHMET1")
    c = TestClient(app_mod.app)
    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    r = c.post("/alexa-sim/turn", headers={"authorization": "Bearer x"},
               json={"utterance": "How is Dad doing today?"})
    assert r.status_code == 200
    kinds = [e for e in c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"]
             if e["kind"] == "alexa"]
    assert kinds and kinds[0]["data"]["tool"] == "get_family_status"
