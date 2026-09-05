"""Running the fleet over one photo's readings, with every tool call traced.

Findings are assembled from the ledger the tools wrote, never parsed from the
models' prose. If the model skips a box, the tool is called directly and the
trace says so: the box is the truth, the model is how it is read.
"""
from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from . import fleet, tools

StepFn = Callable[[dict], None]


@dataclass
class Trace(HookProvider):
    agent_name: str
    on_step: StepFn | None = None
    steps: list[dict] = field(default_factory=list)
    _started: dict[str, float] = field(default_factory=dict)

    def register_hooks(self, registry: HookRegistry, **_) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)
        registry.add_callback(AfterToolCallEvent, self.after)

    def before(self, ev: BeforeToolCallEvent) -> None:
        self._started[ev.tool_use.get("toolUseId", "")] = time.time()

    def after(self, ev: AfterToolCallEvent) -> None:
        tu = ev.tool_use
        t0 = self._started.pop(tu.get("toolUseId", ""), time.time())
        said = ""
        res = ev.result or {}
        for block in res.get("content", []) if isinstance(res, dict) else []:
            if "text" in block:
                said += block["text"]
        step = {"agent": self.agent_name, "tool": tu.get("name"), "input": tu.get("input", {}),
                "said": said.strip(), "ms": int((time.time() - t0) * 1000), "at": time.time()}
        self.steps.append(step)
        if self.on_step:
            self.on_step(step)


def _clean(text: str) -> str:
    """Nova wraps answers in <thinking> and <response> tags. Not for the screen."""
    text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.S)
    return re.sub(r"</?response>", "", text).strip()


def read_boxes(readings: list[dict[str, Any]], on_step: StepFn | None = None) -> dict[str, Any]:
    """`readings` are the Reader's BoxReading dicts. Returns meds + trace + what the agents said."""
    with tools.reading_lock():
        return _read_boxes([r for r in readings if r.get("legible") and r.get("name")], on_step,
                           unreadable=[r for r in readings if not (r.get("legible") and r.get("name"))])


def _read_boxes(readings, on_step, unreadable) -> dict[str, Any]:
    led = tools.open_ledger()
    said: dict[str, str] = {}

    ident_trace = Trace("Identifier", on_step)
    if readings:
        listing = "; ".join(f"name '{r['name']}', strength '{r.get('strength') or ''}', directions '{r.get('directions') or ''}'" for r in readings)
        agent = fleet.identifier([ident_trace])
        said["Identifier"] = _clean(fleet.text_of(agent(f"Boxes photographed: {listing}. Identify each, then parse each box's directions, then report.")))
        for r in readings:  # anything the model skipped is read directly, and the trace says so
            if r["name"] not in led.identities and r["name"] not in led.unconfirmed:
                tools.identify_medicine(r["name"], r.get("strength") or "")
                ident_trace.steps.append({"agent": "Identifier", "tool": "identify_medicine", "input": {"printed_name": r["name"]},
                                          "said": "(read directly; the agent did not ask)", "ms": 0, "at": time.time()})
            if r["name"] not in led.directions:
                tools.parse_directions(r["name"], r.get("directions") or "")

    ingredients = sorted({n.lower() for d in led.identities.values() for _, n in d.get("ingredients", [])})
    watch_trace = Trace("Watchman", on_step)
    if ingredients:
        agent = fleet.watchman([watch_trace])
        said["Watchman"] = _clean(fleet.text_of(agent(f"Ingredients: {', '.join(ingredients)}. Check each once, then report only what is live.")))
        for ing in ingredients:
            if ing not in led.recalls and ing not in led.recall_errors:
                tools.check_for_recalls(ing)

    meds = []
    for r in readings:
        ident = led.identities.get(r["name"])
        ings = [n.lower() for _, n in (ident or {}).get("ingredients", [])]
        recalls = [rec for ing in ings for rec in led.recalls.get(ing, [])]
        meds.append({"id": uuid.uuid4().hex[:10], "printed": r, "name": r["name"], "strength": r.get("strength"), "form": r.get("form"),
                     "identity": ident, "status": "identified" if ident else "unconfirmed",
                     "recalls": recalls[:5], "directions": led.directions.get(r["name"])})
    for r in unreadable:
        meds.append({"id": uuid.uuid4().hex[:10], "printed": r, "name": None, "strength": None, "form": None,
                     "identity": None, "status": "unreadable", "recalls": [], "directions": None})
    return {"meds": meds, "trace": ident_trace.steps + watch_trace.steps, "said": said}


def write_pharmacist_question(finding: dict[str, Any]) -> str:
    return _clean(fleet.text_of(fleet.scribe()(f"Finding: {finding}. Write the question to ask the pharmacist.")))


def write_family_line(facts: dict[str, Any]) -> str:
    return _clean(fleet.text_of(fleet.scribe()(f"Facts about today: {facts}. Write one calm sentence for the daughter.")))


def coach_line(numbers: dict[str, Any]) -> str:
    return _clean(fleet.text_of(fleet.coach()(f"Numbers: {numbers}.")))
