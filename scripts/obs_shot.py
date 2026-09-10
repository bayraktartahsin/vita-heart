#!/usr/bin/env python3
"""Photograph what a scene is showing, through OBS.

The Vega simulator cannot be screenshotted from a script, which has meant designing
the television blind and finding mistakes only when the founder sent a photo of the
screen. OBS is already looking at it, and obs-websocket will hand back a frame.

    python scripts/obs_shot.py                 the television
    python scripts/obs_shot.py --scene FAMILY  the family page
    python scripts/obs_shot.py -o /tmp/x.png
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_director import Obs, _pick_scenes  # noqa: E402


async def shot(role: str, out: Path, width: int) -> int:
    async with Obs() as obs:
        names = [s["sceneName"] for s in (await obs.call("GetSceneList"))["scenes"]]
        scenes = _pick_scenes(names)
        if role not in scenes:
            print(f"no scene for {role} among {names}")
            return 1
        r = await obs.call("GetSourceScreenshot", {"sourceName": scenes[role],
                                                  "imageFormat": "png", "imageWidth": width})
        data = r["imageData"].split(",", 1)[-1]
        out.write_bytes(base64.b64decode(data))
        print(f"{out} ({out.stat().st_size // 1024} KB) — scene '{scenes[role]}'")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", default="TV", choices=["TV", "FAMILY", "ALEXA"])
    ap.add_argument("-o", "--out", default="/tmp/vitaheart-shot.png")
    ap.add_argument("--width", type=int, default=1920)
    a = ap.parse_args()
    try:
        return asyncio.run(shot(a.scene, Path(a.out), a.width))
    except Exception as exc:
        print(f"obs: {exc}\n  Is OBS running with the WebSocket server on?")
        return 1


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
