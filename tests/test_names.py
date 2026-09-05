from agents import names


def test_turkish_brands_map_to_inn():
    assert names.to_inn("PARACETAMOL") == "acetaminophen"
    assert names.to_inn("Coraspin 100 mg") == "aspirin"
    assert names.to_inn("Delix 5 mg tablet") == "ramipril"


def test_unknown_names_are_not_guessed():
    assert names.to_inn("Zxqv 10 mg") is None
    assert names.to_inn(None) is None
