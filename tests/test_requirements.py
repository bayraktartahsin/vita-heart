"""The Lambda bundle and the test environment must agree.

/mcp broke in CI because deploy.py bundled the MCP SDK for the Lambda while
api/requirements.txt never learned about it: every test that imports the app
died on `No module named 'mcp'`. A pin that only one of the two files knows
about is a bug waiting for a deploy.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pins(text: str) -> dict[str, str]:
    pins = {}
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s]+)", line)
        if m:
            pins[m.group(1).lower().replace("_", "-")] = m.group(2)
    return pins


def test_every_bundled_dependency_is_installed_for_the_tests():
    deploy = (ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    deps = _pins("\n".join(re.search(r"^DEPS = \[(.*?)\]", deploy, re.S | re.M)
                           .group(1).replace('"', "").split(",")))
    reqs = _pins((ROOT / "api" / "requirements.txt").read_text(encoding="utf-8"))
    assert deps, "could not read DEPS out of deploy.py"
    for name, version in deps.items():
        assert name in reqs, f"deploy.py bundles {name} but api/requirements.txt does not install it"
        assert reqs[name] == version, f"{name}: Lambda gets {version}, the tests get {reqs[name]}"
