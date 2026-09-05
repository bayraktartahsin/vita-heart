"""The tools the agents may use, and the ledger the app reads afterwards.

Two rules, carried over from VitaCabinet:
  1. A tool tells the model one short sentence and writes the full structured
     result to the ledger. The model orchestrates; the data does not pass
     through it.
  2. Which agent holds which tool is the safety model. The Scribe holds none.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from typing import Any

from strands import tool

from . import names
from .vendored import fda, rxnorm

# Schedule parsing lives in the API package; the agents need the same rules.
try:
    from vitaheart.meds import schedule
except ImportError:  # running from the agents container, where the API package sits next to us
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
    from vitaheart.meds import schedule  # type: ignore


@dataclass
class Ledger:
    identities: dict[str, dict[str, Any]] = field(default_factory=dict)   # by printed name
    unconfirmed: list[str] = field(default_factory=list)
    recalls: dict[str, list[dict[str, Any]]] = field(default_factory=dict) # by ingredient
    recall_errors: dict[str, str] = field(default_factory=dict)
    directions: dict[str, dict[str, Any]] = field(default_factory=dict)   # by printed name


_ledger: Ledger | None = None
_lock = threading.Lock()


def open_ledger() -> Ledger:
    global _ledger
    _ledger = Ledger()
    return _ledger


def ledger() -> Ledger:
    return _ledger if _ledger is not None else open_ledger()


def reading_lock() -> threading.Lock:
    return _lock


@tool
def identify_medicine(printed_name: str, strength: str = "") -> str:
    """Confirm what a printed medicine name is, using the RxNorm vocabulary (NIH).

    Args:
        printed_name: the name exactly as printed on the box, e.g. "CORASPIN" or "Metformin".
        strength: the strength as printed, e.g. "100 mg" (optional).
    """
    led = ledger()
    inn = names.to_inn(printed_name)
    query = " ".join(x for x in ((inn or printed_name), strength) if x)
    try:
        drug = rxnorm.identify(query)
    except Exception as e:  # noqa: BLE001
        led.unconfirmed.append(printed_name)
        return f"RxNorm is unavailable right now ({type(e).__name__}); {printed_name} stays unconfirmed."
    d = asdict(drug)
    if not d.get("rxcui"):
        led.unconfirmed.append(printed_name)
        return f"{printed_name} is not in RxNorm under that name; keep it as printed, unconfirmed."
    d["inn_bridge"] = inn
    led.identities[printed_name] = d
    ingredients = ", ".join(n for _, n in d.get("ingredients", [])) or d.get("name")
    via = f" (sold internationally as {inn})" if inn else ""
    return f"{printed_name}{via} is {d.get('name')} [RxCUI {d['rxcui']}]; ingredient(s): {ingredients}."


@tool
def check_for_recalls(ingredient: str) -> str:
    """Look up live FDA enforcement recalls for one ingredient.

    Args:
        ingredient: an ingredient name, e.g. "aspirin".
    """
    led = ledger()
    try:
        recs = fda.recalls(ingredient, live_only=True)
    except Exception as e:  # noqa: BLE001
        led.recall_errors[ingredient] = type(e).__name__
        return f"The safety record for {ingredient} is unavailable ({type(e).__name__}); nothing is assumed."
    led.recalls[ingredient] = [asdict(r) for r in recs][:10]
    if not recs:
        return f"No live recall for {ingredient}."
    return f"{len(recs)} live recall(s) for {ingredient}; they are against specific batches, and the lot numbers are on the ledger."


@tool
def parse_directions(printed_name: str, directions_text: str) -> str:
    """Turn dosing words into slots (morning, midday, evening, night) without inventing clock times.

    Args:
        printed_name: the medicine these directions belong to.
        directions_text: the dosing words as printed or handwritten, e.g. "Günde 2 kez, yemekten sonra".
    """
    led = ledger()
    d = schedule.parse(directions_text or "")
    led.directions[printed_name] = {"slots": list(d.slots), "food": d.food, "understood": d.understood, "text": d.source_text}
    if not d.understood:
        return f"The directions for {printed_name} were not understood; the television will ask the household."
    return f"{printed_name}: {', '.join(d.slots)}" + (f", {d.food}" if d.food else "") + "."


CLERICAL_TOOLS = [identify_medicine, parse_directions]
SAFETY_TOOLS = [check_for_recalls]
SCRIBE_TOOLS: list = []          # the safety model, in one line
