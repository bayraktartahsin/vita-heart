from agents import names


def test_turkish_brands_map_to_inn():
    assert names.to_inn("PARACETAMOL") == "acetaminophen"
    assert names.to_inn("Coraspin 100 mg") == "aspirin"
    assert names.to_inn("Delix 5 mg tablet") == "ramipril"
    assert names.to_inn("CORA SPIN 100 mg") == "aspirin"     # split at a kerning gap by the reader


def test_unknown_names_are_not_guessed():
    assert names.to_inn("Zxqv 10 mg") is None
    assert names.to_inn(None) is None
"""The brand bridge and the respelling rule that keeps a split brand off the television."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import names


def test_a_brand_split_at_a_kerning_gap_is_respelled():
    assert names.canonical_brand("CORA SPIN") == "CORASPIN"
    assert names.to_inn("CORA SPIN") == "aspirin"


def test_a_name_that_is_already_whole_is_left_alone():
    assert names.canonical_brand("CORASPIN") is None
    assert names.canonical_brand("GLIFOR") is None


def test_two_ordinary_words_are_never_glued_together():
    assert names.canonical_brand("COUGH SYRUP") is None
    assert names.canonical_brand("VITAMIN D") is None
