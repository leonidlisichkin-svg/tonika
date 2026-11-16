"""Checks that need the real language models. They run only in GitHub Actions.

They assert what must hold whatever the models decide: structure, layout, priorities. How often
the models decide right is measured separately by ``tonika eval`` on the golden set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import PROOF_TEXT
from tonika import UserDictionary, analyze, annotate
from tonika.packs import get_pack
from tonika.pipeline import analyze_with as analyze_with_pack
from tonika.text import fold
from tonika.trial import check_preserved

pytestmark = pytest.mark.models

ACUTE = "́"


def test_russian_pack_is_real_and_names_its_version() -> None:
    pack = get_pack("ru")
    assert not pack.demo
    assert pack.tier == "A"
    document = analyze(PROOF_TEXT)
    assert document.model.startswith("stressonnx-")
    assert ":" in document.model


def test_homographs_are_found_with_both_readings() -> None:
    document = analyze(PROOF_TEXT)
    tokens = {token.form: token for token in document.tokens}
    for form, readings in (("замке", {(1,), (4,)}), ("замок", {(1,), (3,)})):
        token = tokens[form]
        assert token.is_ambiguous
        assert {r.stress for r in (token.reading, *token.alternatives)} == readings


def test_a_capitalised_homograph_is_recognised() -> None:
    document = analyze("Замок стоял на холме.")
    token = document.tokens[0]
    assert token.form == "Замок"
    assert token.is_ambiguous
    assert token.reading.stress in {(1,), (3,)}


@pytest.mark.parametrize("mode", ["ambiguous", "all", "yo"])
def test_only_marks_and_yo_are_added(mode: str) -> None:
    text = "Глава 1\n\n— Что?.. — спросил он… И вышел 🙂 , не оглянувшись.\n\tЕще не все (2+2=4)."
    out = annotate(text, target="plus", mode=mode)
    assert fold(out.replace("+", "")) == fold(text.replace("+", ""))
    assert out.count("\n") == text.count("\n")


def test_yo_is_restored() -> None:
    assert annotate("Она еще не вернулась.", target="yo") == "Она ещё не вернулась."


def test_author_marks_and_dictionary_win() -> None:
    dictionary = UserDictionary.parse("+Окленд\nз+амок\n")
    out = annotate("зам+ок, замок и Окленд", target="plus", dictionary=dictionary)
    assert out == "зам+ок, з+амок и +Окленд"


def test_a_long_script_goes_through() -> None:
    text = "В старом замке сломался замок. Она еще не вернулась.\n" * 150
    out = annotate(text, target="plus")
    assert fold(out.replace("+", "")) == fold(text)
    assert out.count("ещё") == 150


TRIAL = Path(__file__).parents[2] / "data" / "trials" / "ru" / "chekhov-lady-with-the-dog.txt"


def test_the_trial_text_is_preserved_and_deterministic() -> None:
    with TRIAL.open(encoding="utf-8", newline="") as handle:
        text = handle.read()
    first = analyze(text)
    assert check_preserved(text, first) is None
    assert sum(1 for token in first.tokens if token.is_ambiguous) > 0
    assert analyze(text).to_json() == first.to_json()


def test_other_languages_get_dictionary_stress() -> None:
    assert annotate("Привіт світ", lang="uk", target="acute") == f"Приві{ACUTE}т світ"
    document = analyze("Сәлем Қазақстан", lang="kk")
    assert document.tokens, "the Kazakh pack marked nothing"
    assert get_pack("kk").tier == "B"


def test_the_model_string_is_known_before_loading_and_matches_after() -> None:
    from tonika.packs import StressonnxPack

    fresh = StressonnxPack("ru")
    described = fresh.model
    assert fresh._backend is None, "reading the model string loaded the model"
    document = analyze_with_pack(fresh, PROOF_TEXT)
    assert fresh._backend is not None
    assert document.model == described == get_pack("ru").model


def test_the_api_answers_with_the_real_model() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tonika.server import Settings, create_app

    client = TestClient(create_app(Settings(pack="auto")))
    response = client.post("/v1/annotate", json={"text": PROOF_TEXT, "target": "plus"})
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "В старом з+амке сломался зам+ок."
    assert data["demo"] is False
    assert data["model"] == get_pack("ru").model
