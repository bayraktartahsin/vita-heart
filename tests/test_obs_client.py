"""Prove the OBS conversation before recording day depends on it.

The authentication digest and the aiming logic are exactly the kind of thing that
looks right and fails once, live, with the founder sitting in front of a camera.
This stands up a fake obs-websocket server and checks what the director actually
says to it.
"""
import asyncio
import base64
import hashlib
import io
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

# What the simulator's window looks like to OBS: a light macOS title bar, the 16:9
# television, and the remote panel beside it that nobody can click.
TITLE_H, SCREEN_W, IMG = 47, 1592, (1920, 940)
SOURCE_W, SOURCE_H = 1160.0, 568.0


def fake_window_png() -> str:
    from PIL import Image
    im = Image.new("RGB", IMG, (233, 233, 235))                       # title bar
    im.paste(Image.new("RGB", (SCREEN_W, IMG[1] - TITLE_H), (10, 13, 18)), (0, TITLE_H))
    im.paste(Image.new("RGB", (IMG[0] - SCREEN_W, IMG[1] - TITLE_H), (60, 60, 60)), (SCREEN_W, TITLE_H))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


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
        if kind == "GetSceneItemTransform":
            return {"sceneItemTransform": {"sourceWidth": SOURCE_W, "sourceHeight": SOURCE_H,
                                           "cropLeft": 0, "cropTop": 0, "cropRight": 0, "cropBottom": 0}}
        if kind == "GetSourceScreenshot":
            return {"imageData": fake_window_png()}
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

    fits = {f["sceneName"]: f["sceneItemTransform"]
            for kind, f in fake.seen if kind == "SetSceneItemTransform"}
    assert len(fits) == 3
    for tr in fits.values():
        assert (tr["boundsWidth"], tr["boundsHeight"]) == (1920, 1080)
        assert tr["boundsType"] == "OBS_BOUNDS_SCALE_INNER"
    # the television is cropped to the screen: the title bar and the remote are gone,
    # measured off the frame rather than hard-coded
    tv = fits["Vega"]
    assert (tv["cropTop"], tv["cropLeft"], tv["cropBottom"]) == (28, 0, 0)
    assert tv["cropRight"] == 198
    kept_w = SOURCE_W - tv["cropLeft"] - tv["cropRight"]
    kept_h = SOURCE_H - tv["cropTop"] - tv["cropBottom"]
    assert abs(kept_w / kept_h - 16 / 9) < 0.01, "what is left must be a 16:9 television"
    # the browser windows are never cropped: their address bar is the proof it runs on AWS
    assert fits["Vita heart"]["cropTop"] == 0 and fits["Alexa"]["cropTop"] == 0


@pytest.mark.asyncio
async def test_a_wrong_password_is_refused_not_silently_ignored(fake, monkeypatch):
    monkeypatch.setattr(d.Obs, "_password", staticmethod(lambda: "wrong"))
    with pytest.raises(Exception):
        async with d.Obs(fake.url):
            pass
    assert not fake.authenticated
