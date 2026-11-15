from __future__ import annotations

from pathlib import Path

import pytest

from tonika import DictionaryError, UserDictionary, analyze, annotate
from tonika.document import Token

SAMPLE = """
# names and places
Окл+енд            # a city
Лис+ичкин*
Корол+ёв
Н+овая Зел+андия
JW Marriott = Джей-Д+абл-ю М+арриотт
"""


def find(text: str, dictionary: str = SAMPLE) -> list[Token]:
    return UserDictionary.parse(dictionary).find(text)


def shown(tokens: list[Token]) -> list[tuple[str, str, tuple[int, ...]]]:
    return [(t.form, t.surface, t.reading.stress) for t in tokens]


def test_word_entry_matches_any_case() -> None:
    assert shown(find("Окленд и ОКЛЕНД, но не Оклендский.")) == [
        ("Окленд", "Окленд", (3,)),
        ("ОКЛЕНД", "ОКЛЕНД", (3,)),
    ]


def test_prefix_entry_matches_longer_forms() -> None:
    assert shown(find("Лисичкин, Лисичкина и Лисичкиным.")) == [
        ("Лисичкин", "Лисичкин", (3,)),
        ("Лисичкина", "Лисичкина", (3,)),
        ("Лисичкиным", "Лисичкиным", (3,)),
    ]


def test_entry_with_yo_restores_it() -> None:
    assert shown(find("Королев и Королёв.")) == [
        ("Королев", "Королёв", (5,)),
        ("Королёв", "Королёв", (5,)),
    ]


def test_phrase_entry() -> None:
    tokens = find("В Новой Зеландии и новая зеландия.")
    assert shown(tokens) == [("новая зеландия", "новая зеландия", (1, 9))]


def test_replacement_entry() -> None:
    tokens = find("Отель JW Marriott открыт.")
    assert shown(tokens) == [("JW Marriott", "Джей-Дабл-ю Марриотт", (6, 13))]
    assert tokens[0].source == "user"
    assert tokens[0].kind == "custom"


def test_longest_match_wins() -> None:
    dictionary = "Н+овая\nН+овая Зел+андия\n"
    assert shown(find("Новая Зеландия и новая жизнь.", dictionary)) == [
        ("Новая Зеландия", "Новая Зеландия", (1, 9)),
        ("новая", "новая", (1,)),
    ]


def test_phrase_needs_word_boundaries() -> None:
    assert find("СуперJW Marriott2") == []


def test_later_entries_override() -> None:
    assert shown(find("замок", "з+амок\nзам+ок\n")) == [("замок", "замок", (3,))]


def test_acute_works_like_plus() -> None:
    assert shown(find("замок", "замо́к\n")) == [("замок", "замок", (3,))]


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("Окленд", "no stress mark"),
        ("123", "no word"),
        ("Нов+ая Зел+андия*", "single word"),
        ("слово* = замена", "cannot have a replacement"),
        ("слово = ", "expected"),
        (" = замена", "expected"),
    ],
)
def test_bad_lines_are_reported_with_their_position(line: str, message: str) -> None:
    with pytest.raises(DictionaryError, match=message) as error:
        UserDictionary.parse(f"# comment\n{line}\n", source="my.dic")
    assert "my.dic:2" in str(error.value)


def test_empty_dictionary() -> None:
    dictionary = UserDictionary.parse("# nothing\n\n")
    assert len(dictionary) == 0
    assert dictionary.find("любой текст") == []


def test_load_merges_files(tmp_path: Path) -> None:
    first = tmp_path / "a.dic"
    second = tmp_path / "b.dic"
    first.write_text("з+амок\nОкл+енд\n", encoding="utf-8")
    second.write_text("зам+ок\n", encoding="utf-8")
    dictionary = UserDictionary.load(first, second)
    assert len(dictionary) == 2
    assert shown(dictionary.find("замок")) == [("замок", "замок", (3,))]


def test_dictionary_overrides_the_pack() -> None:
    text = "В старом замке сломался замок."
    dictionary = UserDictionary.parse("з+амок\n")
    document = analyze(text, pack="fake", dictionary=dictionary)
    lock = document.tokens[-1]
    assert (lock.form, lock.source, lock.reading.stress) == ("замок", "user", (1,))
    # A dictionary reading is marked even in the mode that marks only ambiguous words.
    assert annotate(text, target="plus", pack="fake", dictionary=dictionary) == (
        "В старом з+амке сломался з+амок."
    )


def test_replacement_is_rendered_in_every_notation() -> None:
    dictionary = UserDictionary.parse(SAMPLE)
    text = "Отель JW Marriott в Окленде."
    assert annotate(text, target="plus", pack="fake", dictionary=dictionary) == (
        "Отель Джей-Д+абл-ю М+арриотт в Окленде."
    )
    assert annotate(text, target="yo", pack="fake", dictionary=dictionary) == (
        "Отель Джей-Дабл-ю Марриотт в Окленде."
    )


def test_dictionary_can_be_a_path(tmp_path: Path) -> None:
    path = tmp_path / "names.dic"
    path.write_text("Окл+енд\n", encoding="utf-8")
    assert annotate("Окленд", target="upper", pack="fake", dictionary=path) == "ОклЕнд"


def test_author_mark_beats_the_dictionary() -> None:
    dictionary = UserDictionary.parse("з+амок\n")
    assert annotate("зам+ок и замок", target="plus", pack="fake", dictionary=dictionary) == (
        "зам+ок и з+амок"
    )
