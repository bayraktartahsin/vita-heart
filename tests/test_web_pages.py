"""Every page the demo shows must at least parse. A page that throws on load looks
identical to a page with no data, and the difference was only visible in a console."""
import re
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent / "api" / "vitaheart" / "web"
PAGES = sorted(p.name for p in WEB.glob("*.html"))


@pytest.mark.parametrize("page", PAGES)
def test_inline_script_parses(page, tmp_path):
    html = (WEB / page).read_text(encoding="utf-8")
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    for i, code in enumerate(blocks):
        f = tmp_path / f"{page}.{i}.js"
        f.write_text(code, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{page} block {i}: {r.stderr.splitlines()[:3]}"


def test_every_page_names_the_household_it_reads():
    for page in PAGES:
        html = (WEB / page).read_text(encoding="utf-8")
        if "fetch(" in html:
            assert "household" in html, page


def test_the_surfaces_do_not_wait_on_a_timer_or_a_microphone():
    """Two things that cost a take, and cannot be seen by reading the page in a browser.

    The family page changed on a fifteen-second timer, so the change landed long after
    the sentence it belonged to. The Alexa page armed a microphone in a window that was
    behind two others, with no permission of its own, and silently did nothing.
    """
    web = Path(__file__).resolve().parent.parent / "api" / "vitaheart" / "web"
    family = (web / "family.html").read_text(encoding="utf-8")
    assert "/events?household=" in family, "the family page must be on the live channel"

    alexa = (web / "alexa-sim.html").read_text(encoding="utf-8")
    assert "d.utterance" in alexa and "turn(d.utterance)" in alexa, \
        "the Alexa page must answer the prompter's sentence without the microphone"
    assert "localStorage.getItem('token')" in alexa, \
        "the token must survive a reopened window, or a consent page opens mid-take"


def test_the_alexa_transcript_is_wiped_when_a_take_starts():
    """The setup rehearses this surface for real, and its answer stayed on the page.

    On camera it sat above the question being asked, which reads as the same question
    answered twice — the thing the founder saw and reported.
    """
    page = (Path(__file__).resolve().parent.parent / "api" / "vitaheart" / "web"
            / "alexa-sim.html").read_text(encoding="utf-8")
    assert "d.step === 'record'" in page and "$('log').innerHTML = ''" in page


def test_the_prompter_learns_the_watch_is_on_a_wrist_by_itself():
    """Remembering a toggle is not a plan.

    Forgotten, the television opens a "recorded" session, the replay trace is fed into
    it, and the screen says "a recorded session" while a real Watch sits on a real wrist
    doing nothing.
    """
    page = (Path(__file__).resolve().parent.parent / "api" / "vitaheart" / "web"
            / "prompter.html").read_text(encoding="utf-8")
    assert "c === 'wrist'" in page and "function wristLight" in page
