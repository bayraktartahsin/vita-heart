"""Prove the OBS conversation before recording day depends on it.

The authentication digest and the aiming logic are exactly the kind of thing that
looks right and fails once, live, with the founder sitting in front of a camera.
This stands up a fake obs-websocket server and checks what the director actually
says to it.
"""
import asyncio
import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from websockets.asyncio.server import serve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import obs_director as d  # noqa: E402

PASSWORD = "a-test-password"
SALT, CHALLENGE = "s4lt", "ch4llenge"

WINDOWS = [{"itemName": "[Google Chrome] Vita Heart · Family", "itemValue": 8041},
           {"itemName": "[Google Chrome] Alexa+ · simulated surface · Vita Heart", "itemValue": 9938},
           {"itemName": "[vega-virtual-device] Vega", "itemValue": 7305},
           {"itemName": "[Safari] Vita Heart · prompter", "itemValue": 4242}]

SCENES = {"Vega": "macOS Screen Capture", "Vita heart": "macOS Screen Capture 2",
          "Alexa": "macOS Screen Capture 3"}


class FakeObs:
    def __init__(self):
        self.seen: list[tuple[str, dict]] = []
        self.authenticated = False

    async def handler(self, ws):
        await ws.send(json.dumps({"op": 0, "d": {
            "rpcVersion": 1, "authentication": {"challenge": CHALLENGE, "salt": SALT}}}))
        ident = json.loads(await ws.recv())["d"]
        secret = base64.b64encode(hashlib.sha256((PASSWORD + SALT).encode()).digest()).decode()
        expect = base64.b64encode(hashlib.sha256((secret + CHALLENGE).encode()).digest()).decode()
        if ident.get("authentication") != expect:
            await ws.close()
            return
        self.authenticated = True
        await ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        async for raw in ws:
            msg = json.loads(raw)["d"]
            kind, rid, data = msg["requestType"], msg["requestId"], msg.get("requestData", {})
            self.seen.append((kind, data))
            await ws.send(json.dumps({"op": 7, "d": {
                "requestType": kind, "requestId": rid,
                "requestStatus": {"result": True, "code": 100},
                "responseData": self.reply(kind, data)}}))

    @staticmethod
    def reply(kind: str, data: dict) -> dict:
        if kind == "GetSceneList":
            return {"scenes": [{"sceneName": n} for n in SCENES]}
        if kind == "GetSceneItemList":
            return {"sceneItems": [{"sourceName": SCENES[data["sceneName"]], "sceneItemId": 1,
                                    "inputKind": "screen_capture"}]}
        if kind == "GetInputPropertiesListPropertyItems":
            return {"propertyItems": WINDOWS}
        return {}


@pytest_asyncio.fixture
async def fake(monkeypatch):
    monkeypatch.setattr(d.Obs, "_password", staticmethod(lambda: PASSWORD))
    server = FakeObs()
    async with serve(server.handler, "127.0.0.1", 0) as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        server.url = f"ws://127.0.0.1:{port}"
        yield server


@pytest.mark.asyncio
async def test_it_authenticates_and_aims_every_scene_at_the_right_window(fake):
    async with d.Obs(fake.url) as obs:
        scenes = await d.aim(obs, quiet=True)

    assert fake.authenticated, "the challenge digest was wrong"
    assert scenes == {"TV": "Vega", "FAMILY": "Vita heart", "ALEXA": "Alexa"}

    aimed = {data["inputName"]: data["inputSettings"]["window"]
             for kind, data in fake.seen if kind == "SetInputSettings"}
    assert aimed == {"macOS Screen Capture": 7305,          # the television
                     "macOS Screen Capture 2": 8041,        # the family page
                     "macOS Screen Capture 3": 9938}        # the Alexa surface
    # the prompter must never be captured: it is what the founder is reading
    assert 4242 not in aimed.values()

    fits = [data for kind, data in fake.seen if kind == "SetSceneItemTransform"]
    assert len(fits) == 3
    for f in fits:
        t = f["sceneItemTransform"]
        assert (t["boundsWidth"], t["boundsHeight"]) == (1920, 1080)
        assert t["boundsType"] == "OBS_BOUNDS_SCALE_INNER"


@pytest.mark.asyncio
async def test_a_wrong_password_is_refused_not_silently_ignored(fake, monkeypatch):
    monkeypatch.setattr(d.Obs, "_password", staticmethod(lambda: "wrong"))
    with pytest.raises(Exception):
        async with d.Obs(fake.url):
            pass
    assert not fake.authenticated
