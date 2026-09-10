#!/usr/bin/env python3
"""The director: OBS follows the prompter, so the take needs no hands.

Switching scenes with a function key while reading a sentence is the part of a
demo recording that goes wrong, and it goes wrong silently — you find out when
you watch it back. The prompter already knows which surface each line belongs
to. This connects to the OBS WebSocket server, points each scene at the right
window, and then switches the camera on the household's own events channel as
the prompter moves through the script. It can start and stop the recording too.

  python scripts/obs_director.py --setup    point the scenes at the windows, exit
  python scripts/obs_director.py            do that, then follow the prompter

Nothing here is required to record: without it you press F1/F2/F3 by hand, as
before. The password is read from OBS's own config file and never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

import httpx
import websockets
from websockets.exceptions import WebSocketException

API = "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com"
HOUSEHOLD = "AHMET1"
OBS_CONFIG = Path.home() / "Library/Application Support/obs-studio/plugin_config/obs-websocket/config.json"
CANVAS = (1920, 1080)

# Which OBS scene is which surface. The names in the scene collection are the
# founder's own, so match on a word rather than demand a rename. Most specific first:
# "Vita heart" would otherwise answer to a search for the television.
SCENE_RULES = [("ALEXA", ("alexa",)),
               ("TV", ("vega", "televis", "simulator", "tv")),
               ("FAMILY", ("family", "vita"))]

# The window each scene must be looking at, matched against the list OBS itself offers.
WINDOW_RULES = {"TV": ("vega-virtual-device", "vega virtual"),
                "FAMILY": ("family",),
                "ALEXA": ("alexa+",)}


class Obs:
    """The smallest obs-websocket v5 client that can do this job."""

    def __init__(self, url: str = "ws://127.0.0.1:4455"):
        self.url, self.ws, self._id = url, None, 0

    async def __aenter__(self):
        self.ws = await websockets.connect(self.url, max_size=8 << 20, open_timeout=5)
        hello = json.loads(await self.ws.recv())["d"]
        ident: dict = {"rpcVersion": hello["rpcVersion"]}
        if auth := hello.get("authentication"):
            secret = base64.b64encode(hashlib.sha256(
                (self._password() + auth["salt"]).encode()).digest()).decode()
            ident["authentication"] = base64.b64encode(hashlib.sha256(
                (secret + auth["challenge"]).encode()).digest()).decode()
        await self.ws.send(json.dumps({"op": 1, "d": ident}))
        reply = json.loads(await self.ws.recv())
        if reply.get("op") != 2:
            raise RuntimeError("OBS refused the connection: check the WebSocket password")
        return self

    async def __aexit__(self, *_):
        if self.ws:
            await self.ws.close()

    @staticmethod
    def _password() -> str:
        # Read straight out of OBS's config so it is never typed, pasted or logged.
        return json.loads(OBS_CONFIG.read_text()).get("server_password", "")

    async def call(self, kind: str, data: dict | None = None) -> dict:
        self._id += 1
        rid = str(self._id)
        await self.ws.send(json.dumps({"op": 6, "d": {"requestType": kind, "requestId": rid,
                                                      "requestData": data or {}}}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("op") == 7 and msg["d"]["requestId"] == rid:
                status = msg["d"]["requestStatus"]
                if not status["result"]:
                    raise RuntimeError(f"{kind}: {status.get('comment') or status['code']}")
                return msg["d"].get("responseData") or {}


def _pick_scenes(names: list[str]) -> dict[str, str]:
    """Map TV / FAMILY / ALEXA onto the scenes that actually exist."""
    chosen: dict[str, str] = {}
    taken: set[str] = set()
    for role, words in SCENE_RULES:
        for name in names:
            if name in taken:
                continue
            if any(w in name.lower() for w in words):
                chosen[role] = name
                taken.add(name)
                break
    return chosen


async def screen_crop(obs: Obs, source: str, source_w: float, source_h: float) -> dict | None:
    """Find the television inside the simulator's window.

    The Vega window is a macOS title bar, the screen, and a remote nobody can click.
    Cropping to the screen is the difference between the ten-foot design filling the
    frame and it occupying two thirds of it next to a picture of a remote control.
    Measured rather than hard-coded, because the window can be any size.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    r = await obs.call("GetSourceScreenshot", {"sourceName": source, "imageFormat": "png",
                                               "imageWidth": 1920})
    im = Image.open(io.BytesIO(base64.b64decode(r["imageData"].split(",", 1)[-1]))).convert("RGB")
    W, H = im.size
    px = im.load()
    dark = lambda p: sum(p) < 170           # noqa: E731  the app ground; the title bar is light
    deep = lambda p: sum(p) < 110           # noqa: E731  darker than the remote panel beside it
    rows = [sum(1 for x in range(0, W, 4) if dark(px[x, y])) / (W / 4) for y in range(H)]
    top = next((y for y, sh in enumerate(rows) if sh > 0.5), None)
    if top is None:
        return None
    cols = [sum(1 for y in range(top, H, 4) if deep(px[x, y])) / ((H - top) / 4) for x in range(W)]
    wide = [x for x, sh in enumerate(cols) if sh > 0.8]
    if not wide:
        return None
    left, right = wide[0], wide[-1]
    width = right - left + 1
    height = H - top
    # Only trust it if what was found looks like a television: 16:9, and most of the window.
    if not (1.70 < width / height < 1.86) or width < W * 0.5:
        return None
    k = source_w / W                        # the screenshot was scaled; crop is in source pixels
    return {"cropLeft": round(left * k), "cropTop": round(top * (source_h / H)),
            "cropRight": round((W - right - 1) * k), "cropBottom": 0}


async def aim(obs: Obs, quiet: bool = False) -> dict[str, str]:
    """Point every scene at its window and make it fill the frame."""
    names = [s["sceneName"] for s in (await obs.call("GetSceneList"))["scenes"]]
    scenes = _pick_scenes(names)
    for role in ("TV", "FAMILY", "ALEXA"):
        if role not in scenes:
            print(f"  {role:<6} no scene found among {names}")
            continue
        scene = scenes[role]
        items = (await obs.call("GetSceneItemList", {"sceneName": scene}))["sceneItems"]
        capture = next((i for i in items if i["inputKind"] in ("screen_capture", "window_capture")), None)
        if not capture:
            print(f"  {role:<6} '{scene}' has no window capture in it")
            continue
        source = capture["sourceName"]
        try:
            props = await obs.call("GetInputPropertiesListPropertyItems",
                                   {"inputName": source, "propertyName": "window"})
        except RuntimeError as exc:                       # a display capture has no window list
            print(f"  {role:<6} '{scene}' → {exc}")
            continue
        wanted = WINDOW_RULES[role]
        match = next((i for i in props["propertyItems"]
                      if any(w in (i.get("itemName") or "").lower() for w in wanted)), None)
        if not match:
            # Say what OBS can actually see, so a title that changed is a five-second fix
            # rather than a hunt on recording day.
            seen = ", ".join(i.get("itemName", "?") for i in props["propertyItems"][:12])
            print(f"  {role:<6} '{scene}' → no open window matching {wanted}\n"
                  f"         OBS can see: {seen}")
            continue
        await obs.call("SetInputSettings", {"inputName": source, "overlay": True,
                                            "inputSettings": {"type": 1, "window": match["itemValue"]}})
        transform = {"boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                     "boundsWidth": CANVAS[0], "boundsHeight": CANVAS[1],
                     "alignment": 0, "positionX": CANVAS[0] / 2, "positionY": CANVAS[1] / 2,
                     "cropLeft": 0, "cropTop": 0, "cropRight": 0, "cropBottom": 0}
        if role == "TV":
            cur = (await obs.call("GetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": capture["sceneItemId"]}))["sceneItemTransform"]
            crop = await screen_crop(obs, source, cur["sourceWidth"], cur["sourceHeight"])
            if crop:
                transform.update(crop)
            elif not quiet:
                print(f"  {role:<6} could not find the screen in the window; showing all of it")
        # Fit to screen, the same thing Command-F does, so nothing is letterboxed.
        await obs.call("SetSceneItemTransform", {
            "sceneName": scene, "sceneItemId": capture["sceneItemId"],
            "sceneItemTransform": transform})
        if not quiet:
            print(f"  {role:<6} '{scene}' → {match['itemName']}")
    return scenes


async def follow(obs: Obs, scenes: dict[str, str]) -> None:
    """Switch the camera, and run the recording, as the prompter moves."""
    print("director: following the prompter (ctrl-C to stop)")
    cursor = ""
    async with httpx.AsyncClient(timeout=40) as http:
        while True:
            try:
                r = await http.get(f"{API}/events",
                                   params={"household": HOUSEHOLD, "since": cursor, "wait": 20})
                r.raise_for_status()
                body = r.json()
            except Exception:                              # a dropped poll must not end the take
                await asyncio.sleep(1)
                continue
            cursor = body.get("cursor") or cursor
            for ev in body.get("events", []):
                if ev.get("kind") != "demo":
                    continue
                data = ev.get("data") or {}
                step, scene = data.get("step"), data.get("scene")
                if step == "record":
                    with contextlib.suppress(RuntimeError):
                        await obs.call("StartRecord")
                        print("  ● recording")
                elif step == "endrecord":
                    with contextlib.suppress(RuntimeError):
                        await obs.call("StopRecord")
                        print("  ■ stopped — the file is in ~/Movies")
                if scene and scene in scenes:
                    with contextlib.suppress(RuntimeError):
                        await obs.call("SetCurrentProgramScene", {"sceneName": scenes[scene]})
                        print(f"  → {scene}")


OFFLINE = ("director: OBS is not listening.\n"
           "  In OBS: Tools \u2192 WebSocket Server Settings \u2192 tick 'Enable WebSocket server' \u2192 OK.\n"
           "  Without it the recording still works; you press F1/F2/F3 yourself.")

DOWN = (OSError, asyncio.TimeoutError, WebSocketException)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--setup", action="store_true", help="aim the scenes and exit")
    args = ap.parse_args()
    # This usually runs into a log file. Block buffering would leave that log empty for
    # minutes, which is indistinguishable from the director having died.
    sys.stdout.reconfigure(line_buffering=True)
    if args.setup:
        try:
            async with Obs() as obs:
                print("director: connected to OBS")
                await aim(obs)
        except DOWN:
            print(OFFLINE)
            return 1
        except RuntimeError as exc:
            print(f"director: {exc}")
            return 1
        return 0

    # Wait for OBS rather than exit: the switch that turns the server on is inside OBS,
    # so the founder will often flip it after this is already running. Reconnecting also
    # means a restart of OBS mid-setup does not silently end the automation.
    said = False
    while True:
        try:
            async with Obs() as obs:
                print("director: connected to OBS")
                said = False
                await follow(obs, await aim(obs))
        except DOWN:
            if not said:
                print(OFFLINE)
                said = True
        except RuntimeError as exc:
            print(f"director: {exc}")
        await asyncio.sleep(3)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(asyncio.run(main()))
