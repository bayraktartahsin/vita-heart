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
