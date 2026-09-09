"""International and Turkish-market names to the INN that RxNorm knows.

RxNorm is a US vocabulary. A box in an Istanbul kitchen says PARACETAMOL or
CORASPIN; RxNorm knows acetaminophen and aspirin. This table is the bridge.
It is small, curated by hand, and every entry is a well-known equivalence; when
a name is not here and RxNorm does not confirm it, the medicine is stored as
"unconfirmed" and the television says so. No fuzzy matching.
"""
from __future__ import annotations

import re

# lowercase brand or INN as printed  ->  INN (or ingredient list) RxNorm recognises
TO_INN: dict[str, str] = {
    "paracetamol": "acetaminophen", "parol": "acetaminophen", "minoset": "acetaminophen", "tylol": "acetaminophen",
    "coraspin": "aspirin", "ecopirin": "aspirin", "aspirin": "aspirin",
    "majezik": "flurbiprofen", "arveles": "dexketoprofen", "apranax": "naproxen", "voltaren": "diclofenac",
    "glifor": "metformin", "diaformin": "metformin", "glucophage": "metformin", "metformin": "metformin",
    "delix": "ramipril", "ramipril": "ramipril", "beloc": "metoprolol", "norvasc": "amlodipine",
    "concor": "bisoprolol", "dideral": "propranolol", "coversyl": "perindopril", "micardis": "telmisartan",
    "lipitor": "atorvastatin", "ator": "atorvastatin", "crestor": "rosuvastatin", "zocor": "simvastatin",
    "coumadin": "warfarin", "eliquis": "apixaban", "xarelto": "rivaroxaban", "plavix": "clopidogrel",
    "lansor": "lansoprazole", "nexium": "esomeprazole", "pantpas": "pantoprazole", "omeprol": "omeprazole",
    "augmentin": "amoxicillin / clavulanate", "cipro": "ciprofloxacin", "euthyrox": "levothyroxine", "levotiron": "levothyroxine",
    "lasix": "furosemide", "aldactone": "spironolactone", "zyloric": "allopurinol", "ventolin": "albuterol",
}


def canonical_brand(printed_name: str | None) -> str | None:
    """The brand as the table spells it, when a reader split it at a kerning gap.

    Vision models read "CORASPIN" off a packet as "CORA SPIN" often enough that the
    television would otherwise show a name no pharmacy prints. Only a joined pair that is
    itself a known brand is respelled, and only when neither half is a medicine on its own.
    """
    if not printed_name:
        return None
    words = re.sub(r"[^a-zçğıöşü ]", " ", printed_name.lower()).split()
    if len(words) < 2:
        return None
    for a, b in zip(words, words[1:]):
        if a + b in TO_INN and a not in TO_INN and b not in TO_INN:
            return (a + b).upper() if printed_name.isupper() else (a + b).capitalize()
    return None


def to_inn(printed_name: str | None) -> str | None:
    """Map a printed name to an INN, or return None when it is not in the table."""
    if not printed_name:
        return None
    words = re.sub(r"[^a-zçğıöşü ]", " ", printed_name.lower()).split()
    for word in words:
        if word in TO_INN:
            return TO_INN[word]
    # Readers sometimes split a brand at a kerning gap ("CORA SPIN"); try adjacent pairs joined.
    for a, b in zip(words, words[1:]):
        if a + b in TO_INN:
            return TO_INN[a + b]
    return None
