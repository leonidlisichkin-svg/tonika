from __future__ import annotations

import pytest

from tonika import analyze, annotate
from tonika.engines import UnknownEngineError
from tonika.packs import UnknownPackError

ACUTE = "́"


def test_annotate_one_call() -> None:
    text = "В старом замке сломался замок."
    assert annotate(text, target="plus", pack="fake") == "В старом з+амке сломался зам+ок."


def test_output_is_deterministic() -> None:
    text = "В старом замке сломался замок."
    assert analyze(text, pack="fake") == analyze(text, pack="fake")


def test_author_marks_win_and_are_converted_to_the_target_notation() -> None:
    text = f"Дверь на за{ACUTE}мок, а не на з+амок, и ещё замок."
    document = analyze(text, pack="fake")
    assert [(t.form, t.source, t.surface, t.reading.stress) for t in document.tokens] == [
        ("Дверь", "lexicon", "Дверь", (2,)),
        (f"за{ACUTE}мок", "input", "замок", (1,)),
        ("з+амок", "input", "замок", (1,)),
        ("замок", "lexicon", "замок", (3,)),
    ]
    assert annotate(text, target="plus", mode="all", pack="fake") == (
        "Дв+ерь на з+амок, а не на з+амок, и ещё зам+ок."
    )
    assert annotate(text, target="acute", pack="fake") == (
        f"Дверь на за{ACUTE}мок, а не на за{ACUTE}мок, и ещё замо{ACUTE}к."
    )


def test_author_marks_survive_every_mode() -> None:
    text = "з+амок и замок"
    assert annotate(text, target="plus", mode="yo", pack="fake") == "з+амок и замок"
    assert annotate(text, target="upper", mode="yo", pack="fake") == "зАмок и замок"
    # The yo notation has no way to write stress, so the word stays as typed.
    assert annotate(text, target="yo", pack="fake") == "з+амок и замок"


def test_offsets_refer_to_nfc_text() -> None:
    decomposed = "Мой замок."  # "Мой" typed with a combining breve
    document = analyze(decomposed, pack="fake")
    assert document.text == "Мой замок."
    token = document.tokens[0]
    assert document.text[token.start : token.end] == "замок"


def test_target_can_be_an_engine() -> None:
    text = "В старом замке сломался замок."
    assert annotate(text, target="yandex-speechkit", pack="fake") == (
        "В старом з+амке сломался зам+ок."
    )


def test_bad_arguments_fail_before_any_model_runs() -> None:
    with pytest.raises(UnknownEngineError, match="yandex-speechkit"):
        annotate("текст", target="ssml", pack="fake")
    with pytest.raises(ValueError, match="mode"):
        annotate("текст", mode="some", pack="fake")
    with pytest.raises(UnknownPackError):
        analyze("hello", lang="xx", pack="fake")
