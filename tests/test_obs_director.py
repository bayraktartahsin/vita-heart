"""The camera has to land on the right scene, whatever the founder named them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from obs_director import _pick_scenes  # noqa: E402


def test_the_founders_own_scene_names_are_understood():
    # the collection on the recording machine
    assert _pick_scenes(["Vega", "Vita heart", "Alexa"]) == {
        "TV": "Vega", "FAMILY": "Vita heart", "ALEXA": "Alexa"}


def test_a_scene_is_never_used_twice():
    # "Vita heart TV" answers to both rules; whichever claims it, the other must look on
    picked = _pick_scenes(["Vita heart TV", "Alexa", "family page"])
    assert len(set(picked.values())) == len(picked)


def test_a_missing_scene_is_reported_by_its_absence_not_by_a_wrong_guess():
    assert "FAMILY" not in _pick_scenes(["Vega", "Alexa"])
