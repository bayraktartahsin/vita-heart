#!/usr/bin/env python3
"""Drive the whole demo once, without recording, and check every step landed.

Pre-flight proves the pieces answer. It does not prove that the television obeys a
demo step, that the Alexa surface answers without a microphone, or that the family
page changes while the sentence is still being spoken. A take was lost to exactly
that: every step was emitted correctly into surfaces that were not listening.

    python scripts/rehearse.py

Leaves the household back at the start, so it can be run right up to the take.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

API = os.environ.get("VITAHEART_API", "https://rrjb1x8j2b.execute-api.eu-north-1.amazonaws.com")
HH = "AHMET1"
ok_all = True


def check(name: str, cond: bool, detail: str = "") -> bool:
    global ok_all
    ok_all &= bool(cond)
    print(f"{'OK  ' if cond else 'FAIL'} {name}{(': ' + detail) if detail else ''}", flush=True)
    return bool(cond)


def drive(step: str, **kw) -> None:
    httpx.post(f"{API}/demo", json={"household": HH, "step": step, **kw}, timeout=30)


def until(fn, seconds: float = 12.0, gap: float = 0.6):
    """Wait for a server-side fact, the way the camera waits for the screen."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            got = fn()
        except Exception:
            got = None
        if got:
            return got
        time.sleep(gap)
    return None


def board() -> dict:
    return httpx.get(f"{API}/board", params={"household": HH}, timeout=30).json()


def loudness(path: Path) -> tuple[float, float] | None:
    """mean and peak dB of a file's audio, straight from ffmpeg."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path),
                        "-map", "0:a", "-af", "volumedetect", "-f", "null", "/dev/null"],
                       capture_output=True, text=True)
    vals = {}
    for line in r.stderr.splitlines():
        for key in ("mean_volume", "max_volume"):
            if key in line:
                with_unit = line.split(key + ":")[1].strip()
                vals[key] = float(with_unit.split()[0])
    if "mean_volume" not in vals:
        return None
    return vals["mean_volume"], vals.get("max_volume", vals["mean_volume"])


async def _record_seconds(seconds: float) -> tuple[Path | None, str]:
    """Record briefly, and say which microphone OBS was listening to."""
    from obs_director import Obs
    async with Obs() as obs:
        mic = "unknown"
        try:
            chosen = (await obs.call("GetInputSettings",
                                     {"inputName": "Mic/Aux"}))["inputSettings"].get("device_id", "default")
            devices = (await obs.call("GetInputPropertiesListPropertyItems",
                                      {"inputName": "Mic/Aux",
                                       "propertyName": "device_id"}))["propertyItems"]
            names = {d.get("itemValue"): d.get("itemName") for d in devices}
            mic = names.get(chosen, chosen)
            if chosen == "default":
                # "Default" hides which device it actually is, and on this machine the
                # built-in microphone reaches OBS as digital silence while the AirPods work.
                airpods = [n for n in names.values() if n and "airpod" in n.lower()]
                mic = f"Default ({'AirPods available' if airpods else 'no AirPods connected'})"
        except Exception:
            pass
        if (await obs.call("GetRecordStatus"))["outputActive"]:
            return None, mic
        await obs.call("StartRecord")
        await asyncio.sleep(seconds)
        out = await obs.call("StopRecord")
        return (Path(out["outputPath"]) if out.get("outputPath") else None), mic


def audio_check() -> None:
    """Record a few quiet seconds and look inside the file.

    This is the check that was missing. OBS had microphone permission, the source was
    unmuted, its level was 0 dB and it was on every track — and the recording was pure
    digital silence, because the device itself was not delivering anything to OBS. From
    outside, a dead microphone and a quiet room are the same thing; from inside the file
    they are -91 dB and a noise floor.
    """
    try:
        path, mic = asyncio.run(_record_seconds(3.5))
    except Exception as exc:
        print(f"     (could not test the audio: {exc})")
        return
    if not path:
        print("     (OBS was already recording; audio not tested)")
        return
    time.sleep(1.5)
    got = loudness(path) if path.exists() else None
    try:
        path.unlink()
    except OSError:
        pass
    if not got:
        check("the recording has an audio track", False, "no audio stream in the file")
        return
    mean, peak = got
    # a live microphone always has a noise floor; digital silence is about -91 dB
    live = peak > -85.0
    check("a microphone is reaching the recording", live,
          f"{mic} · peak {peak:.0f} dB, mean {mean:.0f} dB" if live else
          f"{mic} is delivering silence. Put the AirPods in and keep them in — the "
          f"built-in microphone does not reach OBS on this machine.")


def main() -> int:
    print("rehearsal: nothing is being recorded\n")
    httpx.post(f"{API}/demo/reset", json={"household": HH}, timeout=30)
    time.sleep(1.5)

    # 1. the television has to be listening, not merely lit
    cur = httpx.get(f"{API}/events", params={"household": HH, "wait": 0}, timeout=30).json()["cursor"]
    beat = until(lambda: [e for e in httpx.get(
        f"{API}/events", params={"household": HH, "since": cur, "wait": 12}, timeout=30).json()["events"]
        if e["kind"] == "prompter" and (e["data"] or {}).get("cmd") in ("alive", "device")], 26)
    if not check("the television is listening (it beats every 10 s)", bool(beat),
                 "" if beat else "relaunch it: sh scripts/demo_day.sh"):
        print("\nNOT READY — nothing below would have worked either")
        return 1

    # 2. every step the prompter sends, and the fact it must produce
    drive("checkin", scene="TV")
    check("'I'm up' reaches the board", bool(until(lambda: board().get("checkedInToday"))))

    drive("meds", scene="TV")
    time.sleep(1.5)
    due = [d for d in board()["dueDoses"] if not d["unscheduled"]]
    check("a dose is due for the medicine screen", bool(due),
          ", ".join(f"{d['name']} {d['slot']}" for d in due) or "run demo_setup.py --due-now")

    drive("confirm", scene="TV")
    check("the tablet is confirmed on the television",
          bool(until(lambda: [d for d in board()["dueDoses"] if d["confirmed"]])))

    # 3. the Alexa surface, with no microphone in the loop
    cur = httpx.get(f"{API}/events", params={"household": HH, "wait": 0}, timeout=30).json()["cursor"]
    drive("listen", scene="ALEXA", utterance="How is Dad doing today?")
    turn = until(lambda: [e for e in httpx.get(
        f"{API}/events", params={"household": HH, "since": cur, "wait": 15}, timeout=30).json()["events"]
        if e["kind"] == "alexa"], 40)
    check("Alexa answers the prompter's sentence by itself", bool(turn),
          "" if turn else "the page is not connected, or not polling")

    # 4. the session
    drive("session", source="recorded", scene="TV")
    live = until(lambda: httpx.get(f"{API}/session/live", params={"household": HH},
                                   timeout=30).json()["live"])
    check("the session opens on the television", bool(live), (live or {}).get("source", ""))
    if live:
        hr = until(lambda: [e for e in httpx.get(
            f"{API}/events", params={"household": HH, "wait": 12}, timeout=30).json()["events"]
            if e["kind"] == "hr"], 25)
        check("heart rate is arriving", bool(hr),
              f"{hr[-1]['data']['bpm']} bpm" if hr else "the replay daemon is not running")
    drive("stop", scene="TV")
    check("the session closes", until(lambda: httpx.get(
        f"{API}/session/live", params={"household": HH}, timeout=30).json()["live"] is None) is not None
        or httpx.get(f"{API}/session/live", params={"household": HH}, timeout=30).json()["live"] is None)

    drive("family", scene="FAMILY")
    time.sleep(1.5)
    today = httpx.get(f"{API}/family/summary", params={"household": HH}, timeout=30).json()
    check("the family page has something to show", bool(today.get("summary")))

    # 5. the sound, which cannot be judged from outside the file
    audio_check()

    # 6. put it back
    httpx.post(f"{API}/demo/reset", json={"household": HH}, timeout=30)
    print("\nback at the start." if ok_all else "\nNOT READY")
    print("REHEARSAL PASSED" if ok_all else "fix the FAIL lines before recording")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
