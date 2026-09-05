from datetime import datetime, timezone

from fastapi.testclient import TestClient


def client(ddb):
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def seed_med(code="AHMET1", slots=("morning", "evening")):
    from vitaheart import store
    store.put_med(code, {"id": "m1", "name": "PARACETAMOL", "strength": "500 mg", "status": "identified",
                         "directions": {"slots": list(slots), "food": "with food", "understood": True, "text": "twice daily"},
                         "recalls": []})


def test_due_doses_are_unscheduled_until_the_clock_is_set(ddb):
    c = client(ddb)
    seed_med()
    b = c.get("/board", params={"household": "AHMET1"}).json()
    assert len(b["dueDoses"]) == 2 and all(d["unscheduled"] for d in b["dueDoses"])


def test_clock_then_confirm(ddb, monkeypatch):
    from vitaheart.meds import service
    c = client(ddb)
    seed_med()
    assert c.post("/clock", json={"household": "AHMET1", "times": {"morning": "08:00", "evening": "19:00"}}).status_code == 200
    # Freeze "now" at 08:10 Istanbul (05:10 UTC): the morning dose is due, the evening one is not.
    monkeypatch.setattr(service, "datetime", _Frozen(datetime(2026, 9, 5, 5, 10, tzinfo=timezone.utc)))
    b = c.get("/board", params={"household": "AHMET1"}).json()
    due = [d for d in b["dueDoses"] if not d["unscheduled"]]
    assert [d["slot"] for d in due] == ["morning"] and due[0]["confirmed"] is False
    r = c.post("/doses/confirm", json={"household": "AHMET1", "dose_id": due[0]["id"], "by": "remote"})
    assert r.status_code == 201
    b2 = c.get("/board", params={"household": "AHMET1"}).json()
    assert [d for d in b2["dueDoses"] if d["slot"] == "morning"][0]["confirmed"] is True
    ev = c.get("/events", params={"household": "AHMET1", "wait": 0}).json()
    assert "dose" in [e["kind"] for e in ev["events"]]


def test_rejects_unknown_slot(ddb):
    c = client(ddb)
    assert c.post("/clock", json={"household": "AHMET1", "times": {"dawn": "05:00"}}).status_code == 422


def test_read_refuses_photo_from_another_household(ddb, monkeypatch):
    monkeypatch.setenv("VITAHEART_BUCKET", "b")
    c = client(ddb)
    assert c.post("/meds/read", json={"household": "AHMET1", "key": "OTHER1/x.jpg"}).status_code == 400


class _Frozen:
    """Stand-in for `datetime` inside the service module with a fixed now()."""
    def __init__(self, at):
        self._at = at
    def now(self, tz=None):
        return self._at
    def combine(self, *a, **k):
        return datetime.combine(*a, **k)
