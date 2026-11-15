from __future__ import annotations

import warnings

import pytest

from tonika.packs import (
    DemoPackWarning,
    FakePack,
    LanguagePack,
    UnknownPackError,
    available_packs,
    get_pack,
)
from tonika.text import match_case


def test_fake_pack_follows_the_protocol() -> None:
    pack = FakePack("ru")
    assert isinstance(pack, LanguagePack)
    assert pack.demo
    assert pack.model == "fake-0"


def test_fake_pack_tokens() -> None:
    tokens = FakePack("ru").analyze("В старом замке сломался замок.")
    assert [(t.form, t.reading.stress, t.is_ambiguous) for t in tokens] == [
        ("старом", (2,), False),
        ("замке", (1,), True),
        ("сломался", (4,), False),
        ("замок", (3,), True),
    ]


def test_fake_pack_keeps_case_and_ignores_unknown_words() -> None:
    tokens = FakePack("ru").analyze("ЗАМОК стоит. Все ушли.")
    assert [t.form for t in tokens] == ["ЗАМОК", "Все"]
    assert tokens[1].surface == "Всё"


def test_fake_pack_rejects_unknown_language() -> None:
    with pytest.raises(ValueError):
        FakePack("xx")


def test_auto_falls_back_to_demo_pack_with_a_warning() -> None:
    with pytest.warns(DemoPackWarning):
        pack = get_pack("ru")
    assert pack.demo


def test_explicit_fake_pack_does_not_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        get_pack("ru", "fake")


def test_unknown_language_or_pack() -> None:
    with pytest.raises(UnknownPackError, match="no language pack"):
        get_pack("xx", "fake")
    with pytest.raises(UnknownPackError, match="unknown pack"):
        get_pack("ru", "nope")


def test_available_packs() -> None:
    assert available_packs() == {"ru": ["fake"]}


@pytest.mark.parametrize(
    ("template", "word", "expected"),
    [("все", "всё", "всё"), ("Все", "всё", "Всё"), ("ВСЕ", "всё", "ВСЁ"), ("Ab", "xyz", "Xyz")],
)
def test_match_case(template: str, word: str, expected: str) -> None:
    assert match_case(template, word) == expected
