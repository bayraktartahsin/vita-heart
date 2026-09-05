import json

from fastapi.testclient import TestClient

from vitaheart import ring

KEY = b"test-hmac-key"


def client(ddb, monkeypatch):
    monkeypatch.setenv("VITAHEART_RING_HMAC_KEY", KEY.decode())
    from vitaheart import seed, app as appmod
    seed.main()
    return TestClient(appmod.app)


def post(c, payload, key=KEY):
    body = json.dumps(payload).encode()
    return c.post("/ring/webhook?household=AHMET1", content=body,
                  headers={"content-type": "application/json", "X-Signature": ring.sign(body, key)})


def test_valid_signature_stores_a_normalised_signal(ddb, monkeypatch):
    c = client(ddb, monkeypatch)
    r = post(c, {"event_type": "contact_opened", "device_name": "front door", "timestamp": "2026-09-05T00:10:00Z",
                 "meta": {"request_id": "r1", "account_id": "a"}})
    assert r.status_code == 200 and r.json()["kind"] == "contact.open" and r.json()["value"] == "open"
    sig = c.get("/signals", params={"household": "AHMET1", "hours": 168}).json()["signals"]
    assert [s["kind"] for s in sig] == ["contact.open"]


def test_bad_signature_is_refused_and_stored_nowhere(ddb, monkeypatch):
    c = client(ddb, monkeypatch)
    assert post(c, {"event_type": "motion_detected"}, key=b"wrong").status_code == 401
    assert c.get("/signals", params={"household": "AHMET1"}).json()["signals"] == []


def test_duplicate_request_id_is_one_signal(ddb, monkeypatch):
    c = client(ddb, monkeypatch)
    p = {"event_type": "motion_detected", "device_id": "cam-1", "meta": {"request_id": "same"}}
    assert post(c, p).json()["duplicate"] is False
    assert post(c, p).json()["duplicate"] is True
    assert len(c.get("/signals", params={"household": "AHMET1"}).json()["signals"]) == 1


def test_float_values_are_stored(ddb, monkeypatch):
    c = client(ddb, monkeypatch)
    r = post(c, {"event_type": "temperature_reading", "device_name": "hall", "data": {"temperature_c": 16.8}, "meta": {"request_id": "t1"}})
    assert r.status_code == 200
    assert c.get("/signals", params={"household": "AHMET1"}).json()["signals"][0]["value"] == 16.8


def test_unknown_event_types_are_kept_with_a_ring_prefix():
    n = ring.normalise({"event_type": "subscription_activated", "device_id": "x"})
    assert n["kind"] == "ring.subscription_activated"
    t = ring.normalise({"event_type": "temperature_reading", "device_name": "hall", "data": {"temperature_c": 16.5}})
    assert t["kind"] == "temperature" and t["value"] == 16.5
