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
