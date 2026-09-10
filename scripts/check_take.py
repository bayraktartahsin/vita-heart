#!/usr/bin/env python3
"""Judge a finished recording against the rules before it is uploaded.

    python scripts/check_take.py            the newest file in ~/Movies
    python scripts/check_take.py FILE

The rule that matters is length: "Demo video under 3 minutes… judges aren't required to
watch past the 3-minute mark." A take ran 3:52 and nobody knew until it was measured.
The rest is what cannot be seen by watching on a laptop with the volume down: whether
there is narration in it at all, and whether it clipped.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LIMIT = 180.0          # seconds; the rule is "under 3 minutes"
COMFORT = 168.0        # leave the judges a margin, and yourself a title card


def ffprobe(path: Path, args: list[str]) -> str:
    return subprocess.run(["ffprobe", "-v", "error", *args, "-of", "default=nw=1:nk=1",
                           str(path)], capture_output=True, text=True).stdout.strip()


def segments(path: Path, dur: float, step: int = 10) -> list[tuple[int, float]]:
    out = []
    for s in range(0, int(dur), step):
        r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-ss", str(s), "-t", str(step),
                            "-i", str(path), "-map", "0:a", "-af", "volumedetect",
                            "-f", "null", "/dev/null"], capture_output=True, text=True)
        mean = next((float(l.split("mean_volume:")[1].split()[0])
                     for l in r.stderr.splitlines() if "mean_volume:" in l), -91.0)
        out.append((s, mean))
    return out


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        movies = sorted(Path.home().joinpath("Movies").glob("*.mp4"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
        if not movies:
            print("no recordings in ~/Movies")
            return 1
        path = movies[0]
    print(f"{path.name}\n")

    ok = True
    dur = float(ffprobe(path, ["-show_entries", "format=duration"]) or 0)
    mm, ss = int(dur // 60), int(dur % 60)
    if dur >= LIMIT:
        ok = False
        print(f"FAIL length {mm}:{ss:02d} — the rule is under 3:00, and judges are not "
              f"required to watch past it. Over by {dur - LIMIT:.0f} s.")
    elif dur > COMFORT:
        print(f"OK   length {mm}:{ss:02d} — under 3:00, but only by {LIMIT - dur:.0f} s")
    else:
        print(f"OK   length {mm}:{ss:02d}")

    size = ffprobe(path, ["-select_streams", "v", "-show_entries", "stream=width,height"]).split()
    if size[:2] == ["1920", "1080"]:
        print("OK   1920x1080")
    else:
        ok = False
        print(f"FAIL resolution {'x'.join(size[:2])} — judges watch this full screen")

    if not ffprobe(path, ["-select_streams", "a", "-show_entries", "stream=codec_name"]):
        print("FAIL no audio track at all")
        return 1

    segs = segments(path, dur)
    quiet = [s for s, m in segs if m < -60]
    peak = float(next((l.split("max_volume:")[1].split()[0] for l in subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-map", "0:a",
         "-af", "volumedetect", "-f", "null", "/dev/null"],
        capture_output=True, text=True).stderr.splitlines() if "max_volume:" in l), "-91"))
    body = [s for s in quiet if s < dur - 12]        # a quiet tail is the ending, not a fault
    if body:
        ok = False
        where = ", ".join(f"{s // 60}:{s % 60:02d}" for s in body[:6])
        print(f"FAIL silence in the body at {where} — no narration reached those seconds")
    else:
        print(f"OK   narration throughout ({len(segs)} ten-second windows checked)")

    if peak > -0.5:
        print(f"OK   peak {peak:.1f} dB — at the ceiling; check it does not sound harsh")
    else:
        print(f"OK   peak {peak:.1f} dB")

    print("\nUPLOAD" if ok else "\nDO NOT UPLOAD — fix the FAIL lines and record again")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
