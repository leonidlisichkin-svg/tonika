from __future__ import annotations

import pytest

from tonika.segment import iter_chunks


def chunks(text: str, max_chars: int = 600) -> list[str]:
    spans = list(iter_chunks(text, max_chars))
    # Spans must cover the text exactly, in order.
    assert "".join(text[start:end] for start, end in spans) == text
    assert all(start < end for start, end in spans)
    return [text[start:end] for start, end in spans]


def test_sentences() -> None:
    assert chunks("Он вошёл. Замок был пуст! «Кто здесь?» — спросил он.") == [
        "Он вошёл. ",
        "Замок был пуст! ",
        "«Кто здесь?» — спросил он.",
    ]


def test_closing_quotes_and_ellipsis_stay_with_their_sentence() -> None:
    assert chunks("«Тихо…» Он замер. Потом шагнул.") == ["«Тихо…» ", "Он замер. ", "Потом шагнул."]


def test_abbreviation_before_a_lowercase_word_does_not_split() -> None:
    assert chunks("Это т. е. так и было. Да.") == ["Это т. е. так и было. ", "Да."]


def test_line_breaks_always_split() -> None:
    assert chunks("Глава 1\n\nстарый замок\nи дверь") == [
        "Глава 1\n\n",
        "старый замок\n",
        "и дверь",
    ]


def test_long_sentence_is_cut_at_punctuation_or_space() -> None:
    sentence = "слово, " * 40 + "конец."
    parts = chunks(sentence, max_chars=60)
    assert len(parts) > 1
    assert all(len(part) <= 60 for part in parts)
    assert all(part.endswith(", ") for part in parts[:-1])


def test_text_without_spaces_is_cut_hard() -> None:
    parts = chunks("а" * 25, max_chars=10)
    assert [len(part) for part in parts] == [10, 10, 5]


def test_empty_text_and_bad_limit() -> None:
    assert chunks("") == []
    with pytest.raises(ValueError):
        list(iter_chunks("текст", 0))
