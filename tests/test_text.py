from __future__ import annotations

import pytest

from tonika.text import (
    count_vowels,
    fold,
    is_author_marked,
    iter_words,
    locate_marks,
    lower,
    match_case,
    split_marks,
    strip_author_marks,
)

ACUTE = "́"


def words(text: str) -> list[str]:
    return [word for _, _, word in iter_words(text)]


def test_words_are_letter_runs() -> None:
    assert words("Кто-то сказал: «Привет, мир!» 2 раза") == [
        "Кто",
        "то",
        "сказал",
        "Привет",
        "мир",
        "раза",
    ]


def test_plus_belongs_to_a_word_only_before_a_cyrillic_vowel() -> None:
    assert words("зам+ок и +атлас") == ["зам+ок", "и", "+атлас"]
    assert words("2+2, A+B, C++, плюс+минус, +7") == ["A", "B", "C", "плюс", "минус"]


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("зам+ок", ("замок", (3,))),
        (f"замо{ACUTE}к", ("замок", (3,))),
        ("+атлас", ("атлас", (0,))),
        (f"вода{ACUTE}", ("вода", (3,))),
        ("замок", ("замок", ())),
        ("н+аучно-техн+ический", ("научно-технический", (1, 11))),
        (f"за{ACUTE}м+ок", ("замок", (1, 3))),
    ],
)
def test_split_marks(word: str, expected: tuple[str, tuple[int, ...]]) -> None:
    assert split_marks(word) == expected


def test_acute_after_a_consonant_is_not_a_stress_mark() -> None:
    word = f"с{ACUTE}он"
    assert split_marks(word) == (word, ())
    assert not is_author_marked(word)


def test_lower_and_fold_keep_length() -> None:
    assert lower("ЁЖ İstanbul") == "ёж istanbul"
    assert len(lower("İ")) == 1
    assert fold("Всё ЕЩЁ") == "все еще"


def test_count_vowels() -> None:
    assert count_vowels("дверь") == 1
    assert count_vowels("Замок") == 2
    assert count_vowels("привіт") == 2
    assert count_vowels("bcd") == 0


def test_strip_author_marks_maps_back_to_the_original() -> None:
    text = f"Дверь на за{ACUTE}мок, +атлас, вода{ACUTE} и зам+ок."
    clean = strip_author_marks(text)
    assert clean.text == "Дверь на замок, атлас, вода и замок."
    assert [clean.text[w.start : w.end] for w in clean.author_words] == [
        "замок",
        "атлас",
        "вода",
        "замок",
    ]
    assert [w.stress for w in clean.author_words] == [(1,), (0,), (3,), (3,)]
    assert [text.__getitem__(slice(*clean.span(w.start, w.end))) for w in clean.author_words] == [
        f"за{ACUTE}мок",
        "+атлас",
        f"вода{ACUTE}",
        "зам+ок",
    ]
    # Unmarked text maps to itself.
    start = clean.text.index("Дверь")
    assert clean.span(start, start + 5) == (0, 5)


def test_strip_author_marks_without_marks_is_identity() -> None:
    text = "Обычный текст, 2+2 и C++."
    clean = strip_author_marks(text)
    assert clean.text == text
    assert clean.author_words == ()
    assert clean.span(0, len(text)) == (0, len(text))


@pytest.mark.parametrize(
    ("template", "word", "expected"),
    [("все", "всё", "всё"), ("Все", "всё", "Всё"), ("ВСЕ", "всё", "ВСЁ"), ("Ab", "xyz", "Xyz")],
)
def test_match_case(template: str, word: str, expected: str) -> None:
    assert match_case(template, word) == expected


def test_locate_marks_in_an_unchanged_text() -> None:
    source = "Все знали про замок."
    marked = f"Всё зна{ACUTE}ли про замо{ACUTE}к."
    assert locate_marks(source, marked) == ([6, 17], [2])


def test_locate_marks_when_characters_were_dropped() -> None:
    source = "Замок… стоял , как прежде 🙂!"
    marked = f"замо{ACUTE}к стоя{ACUTE}л, как пре{ACUTE}жде!"
    stress, yo = locate_marks(source, marked)
    assert [source[i] for i in stress] == ["о", "я", "е"]
    assert stress == [3, 10, 21]
    assert yo == []


def test_locate_marks_drops_what_it_cannot_trace() -> None:
    source = "замок"
    marked = f"совсе{ACUTE}м другое замо{ACUTE}к"
    stress, _ = locate_marks(source, marked)
    assert stress == [3]


def test_locate_marks_ignores_a_leading_mark() -> None:
    assert locate_marks("да", f"{ACUTE}да{ACUTE}") == ([1], [])
