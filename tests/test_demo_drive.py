"""The autopilot the prompter uses during a recording.

Nothing here is a demo-only code path: each step is the call the on-screen button makes.
The test exists because the recording depends on it, and a broken step would only show
up with a camera running."""
from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def test_each_step_reaches_the_television_on_the_events_channel(ddb):
    c = client(ddb)
    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    for step in ("checkin", "meds", "confirm", "session", "stop", "family", "listen"):
        assert c.post("/demo", json={"household": "AHMET1", "step": step}).status_code == 200
    events = c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"]
    steps = [e["data"]["step"] for e in events if e["kind"] == "demo"]
    assert steps == ["checkin", "meds", "confirm", "session", "stop", "family", "listen"]


def test_a_session_source_is_carried_so_the_screen_can_label_it(ddb):
    c = client(ddb)
    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    c.post("/demo", json={"household": "AHMET1", "step": "session", "source": "recorded"})
    e = [x for x in c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"] if x["kind"] == "demo"]
    assert e[0]["data"]["source"] == "recorded"


def test_an_unknown_household_is_refused(ddb):
    c = client(ddb)
    assert c.post("/demo", json={"household": "NOBODY", "step": "checkin"}).status_code == 404


def test_a_nonsense_source_is_refused(ddb):
    c = client(ddb)
    assert c.post("/demo", json={"household": "AHMET1", "step": "session", "source": "made-up"}).status_code == 422


def test_the_scene_reaches_the_director_so_the_camera_can_follow(ddb):
    c = client(ddb)
    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    c.post("/demo", json={"household": "AHMET1", "step": "scene", "scene": "FAMILY"})
    e = [x for x in c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"]
         if x["kind"] == "demo"]
    assert e[0]["data"]["scene"] == "FAMILY"


def test_a_scene_that_is_not_one_of_the_three_is_refused(ddb):
    c = client(ddb)
    assert c.post("/demo", json={"household": "AHMET1", "step": "scene",
                                 "scene": "TERMINAL"}).status_code == 422


def test_start_again_clears_the_day_and_sends_the_television_home(ddb):
    c = client(ddb)
    c.post("/checkin", json={"household": "AHMET1"})
    board = c.get("/board", params={"household": "AHMET1"}).json()
    assert board["checkedInToday"] is True
    due = [d for d in board["dueDoses"] if not d["unscheduled"]]
    if due:
        c.post("/meds/confirm", json={"household": "AHMET1", "dose": due[0]["id"]})
    c.post("/session/start", json={"household": "AHMET1", "source": "recorded"})

    cursor = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()["cursor"]
    r = c.post("/demo/reset", json={"household": "AHMET1"})
    assert r.status_code == 200 and r.json()["ok"] is True

    after = c.get("/board", params={"household": "AHMET1"}).json()
    assert after["checkedInToday"] is False
    assert not [d for d in after["dueDoses"] if d["confirmed"]]
    assert c.get("/session/live", params={"household": "AHMET1"}).json()["live"] is None
    steps = [e["data"] for e in c.get("/events", params={"household": "AHMET1", "since": cursor, "wait": 0}).json()["events"]
             if e["kind"] == "demo"]
    assert steps and steps[-1]["step"] == "board"


def test_start_again_keeps_the_medicines(ddb):
    # the labels cost a model call to rebuild; they are never what goes wrong in a take
    c = client(ddb)
    before = c.get("/meds", params={"household": "AHMET1"}).json()["meds"]
    c.post("/demo/reset", json={"household": "AHMET1"})
    assert c.get("/meds", params={"household": "AHMET1"}).json()["meds"] == before


def test_stopping_the_session_rewrites_tonights_summary(ddb, monkeypatch):
    """The summary is a snapshot, and a stale one contradicts the screen beside it.

    On camera it said no dose was confirmed and no session was done, seconds after the
    judges watched both — and the narration was pointing straight at it.
    """
    from vitaheart.night import watch
    calls: list[str] = []
    monkeypatch.setattr(watch, "run_for",
                        lambda hh, notify=True: calls.append(hh) or {"ok": True})
    c = client(ddb)
    c.post("/demo", json={"household": "AHMET1", "step": "meds"})
    assert calls == [], "only stopping the session should rewrite it"
    r = c.post("/demo", json={"household": "AHMET1", "step": "stop"})
    assert r.status_code == 200
    assert calls == ["AHMET1"]


def test_a_failing_summary_refresh_never_breaks_the_take(ddb, monkeypatch):
    from vitaheart.night import watch
    monkeypatch.setattr(watch, "run_for",
                        lambda hh, notify=True: (_ for _ in ()).throw(RuntimeError("bedrock down")))
    c = client(ddb)
    assert c.post("/demo", json={"household": "AHMET1", "step": "stop"}).status_code == 200


def test_start_again_also_rewrites_the_summary_for_the_cleared_day(ddb, monkeypatch):
    """Otherwise the next take opens describing the last one.

    At 0:25 of a take the family page said "0 of 2 doses confirmed" in one panel and
    "1 of 2 scheduled doses were confirmed, and there was a seated session of 12
    seconds" in the other — the previous run's day, on a page whose whole argument is
    that it states only facts.
    """
    from vitaheart.night import watch
    calls: list[str] = []
    monkeypatch.setattr(watch, "run_for", lambda hh, notify=True: calls.append(hh) or {})
    c = client(ddb)
    assert c.post("/demo/reset", json={"household": "AHMET1"}).status_code == 200
    assert calls == ["AHMET1"]
