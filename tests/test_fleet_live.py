"""Live: the Strands fleet over two readings (RxNorm, openFDA, Bedrock). VITAHEART_LIVE=1."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytestmark = pytest.mark.skipif(not os.environ.get("VITAHEART_LIVE"), reason="set VITAHEART_LIVE=1")


def test_fleet_reads_two_boxes_and_traces_every_tool_call():
    from agents import run
    readings = [
        {"name": "CORASPIN", "strength": "100 mg", "form": "tablet", "directions": "Günde 1 kez, sabah", "lot": "25A007", "legible": True},
        {"name": "Metformin", "strength": "850 mg", "form": "tablet", "directions": "twice daily with food", "lot": None, "legible": True},
        {"name": None, "strength": None, "form": None, "directions": None, "lot": None, "legible": False},
    ]
    out = run.read_boxes(readings)
    by = {m["name"]: m for m in out["meds"] if m["name"]}
    assert by["CORASPIN"]["status"] == "identified" and "aspirin" in str(by["CORASPIN"]["identity"]).lower()
    assert by["Metformin"]["status"] == "identified"
    assert by["CORASPIN"]["directions"]["slots"] == ["morning"]
    assert by["Metformin"]["directions"] == {"slots": ["morning", "evening"], "food": "with food", "understood": True, "text": "twice daily with food"}
    assert any(m["status"] == "unreadable" for m in out["meds"])
    tools_called = {(s["agent"], s["tool"]) for s in out["trace"]}
    assert ("Identifier", "identify_medicine") in tools_called and ("Watchman", "check_for_recalls") in tools_called
    for word in ("monitor", "diagnos", "alarm"):
        assert word not in (out["said"].get("Watchman", "") + out["said"].get("Identifier", "")).lower()
