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
