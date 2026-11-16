"""Checks that need the real language models. They run only in GitHub Actions.

They assert what must hold whatever the models decide: structure, layout, priorities. How often
the models decide right is measured separately by ``tonika eval`` on the golden set.
"""

from __future__ import annotations

import pytest

from helpers import PROOF_TEXT
from tonika import UserDictionary, analyze, annotate
from tonika.packs import get_pack
from tonika.text import fold

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


def test_other_languages_get_dictionary_stress() -> None:
    assert annotate("Привіт світ", lang="uk", target="acute") == f"Приві{ACUTE}т світ"
    document = analyze("Сәлем Қазақстан", lang="kk")
    assert document.tokens, "the Kazakh pack marked nothing"
    assert get_pack("kk").tier == "B"
