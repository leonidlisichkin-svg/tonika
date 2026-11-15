from __future__ import annotations

import pytest

from tonika import IntentDocument, analyze, render
from tonika.render import mark_stress


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("plus", "В старом з+амке сломался зам+ок."),
        ("acute", "В старом за́мке сломался замо́к."),
        ("upper", "В старом зАмке сломался замОк."),
        ("yo", "В старом замке сломался замок."),
    ],
)
def test_notations_in_ambiguous_mode(
    proof_document: IntentDocument, target: str, expected: str
) -> None:
    assert render(proof_document, target=target) == expected


def test_mode_all_marks_unambiguous_words(proof_document: IntentDocument) -> None:
    assert render(proof_document, "plus", "all") == "В ст+аром з+амке слом+ался зам+ок."


def test_respelling_applies_in_every_mode() -> None:
    document = analyze("Еще не все.", lang="ru", pack="fake")
    assert render(document, "plus", "yo") == "Ещё не всё."
    assert render(document, "plus", "ambiguous") == "Ещё не вс+ё."
    assert render(document, "plus", "all") == "Ещ+ё не вс+ё."
    assert render(document, "yo", "all") == "Ещё не всё."


def test_layout_outside_tokens_is_preserved() -> None:
    text = "  Замок!\n\n\t— Какой «замок»?  \n"
    document = analyze(text, lang="ru", pack="fake")
    assert render(document, "plus") == "  Зам+ок!\n\n\t— Какой «зам+ок»?  \n"


def test_unknown_notation_or_mode(proof_document: IntentDocument) -> None:
    with pytest.raises(ValueError, match="notation"):
        render(proof_document, target="ssml")
    with pytest.raises(ValueError, match="mode"):
        render(proof_document, mode="some")


def test_mark_stress_rejects_yo() -> None:
    assert mark_stress("замок", [3], "plus") == "зам+ок"
    with pytest.raises(ValueError):
        mark_stress("замок", [3], "yo")
