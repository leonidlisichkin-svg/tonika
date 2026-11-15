from __future__ import annotations

import pytest

from tonika import analyze, annotate
from tonika.packs import UnknownPackError


def test_annotate_one_call() -> None:
    text = "В старом замке сломался замок."
    assert annotate(text, target="plus", pack="fake") == "В старом з+амке сломался зам+ок."


def test_output_is_deterministic() -> None:
    text = "В старом замке сломался замок."
    assert analyze(text, pack="fake") == analyze(text, pack="fake")


def test_author_marks_are_preserved() -> None:
    text = "Дверь на за́мок, а не на з+амок, и ещё замок."
    document = analyze(text, pack="fake")
    assert [t.form for t in document.tokens] == ["Дверь", "замок"]
    assert annotate(text, target="plus", mode="all", pack="fake") == (
        "Дв+ерь на за́мок, а не на з+амок, и ещё зам+ок."
    )


def test_offsets_refer_to_nfc_text() -> None:
    decomposed = "Мой замок."  # "Мой" typed with a combining breve
    document = analyze(decomposed, pack="fake")
    assert document.text == "Мой замок."
    token = document.tokens[0]
    assert document.text[token.start : token.end] == "замок"


def test_unknown_language() -> None:
    with pytest.raises(UnknownPackError):
        analyze("hello", lang="xx", pack="fake")
