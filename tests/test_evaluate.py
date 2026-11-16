from __future__ import annotations

from pathlib import Path

import pytest

from helpers import ScriptedBackend
from tonika.document import Reading
from tonika.evaluate import (
    ExampleError,
    evaluate,
    load_examples,
    minimum_accuracy,
    parse_marked,
)
from tonika.packs import FakePack, StressonnxPack


def test_parse_marked_sentence() -> None:
    examples = parse_marked("В старом з+амке сломался зам+ок.", "g:1")
    assert [(e.text, e.form, e.reading, e.id) for e in examples] == [
        ("В старом замке сломался замок.", "замке", Reading(stress=(1,)), "g:1.1"),
        ("В старом замке сломался замок.", "замок", Reading(stress=(3,)), "g:1.2"),
    ]


def test_marked_word_with_yo_is_given_without_it() -> None:
    (example,) = parse_marked("Он знал вс+ё, ёлки зелёные.")
    assert example.text == "Он знал все, ёлки зелёные."
    assert (example.form, example.surface, example.reading.stress) == ("все", "всё", (2,))
    (kept,) = parse_marked("Вс+е пришли.")
    assert (kept.text, kept.surface) == ("Все пришли.", "Все")


def test_load_txt_and_jsonl(tmp_path: Path) -> None:
    txt = tmp_path / "ru.txt"
    txt.write_text("# comment\n\nДверь на зам+ок.\n", encoding="utf-8")
    (example,) = load_examples(txt)
    assert (example.form, example.id) == ("замок", "ru:3")

    jsonl = tmp_path / "ru.jsonl"
    jsonl.write_text(
        '{"id": "ru-000001", "lang": "ru", "text": "Дверь заперта на замок.", "start": 17, '
        '"end": 22, "form": "замок", "reading": {"stress": [3]}, "status": "accepted"}\n',
        encoding="utf-8",
    )
    (record,) = load_examples(jsonl)
    assert (record.form, record.reading.stress, record.id) == ("замок", (3,), "ru-000001")


@pytest.mark.parametrize(
    "line",
    [
        '{"text": "замок", "start": 0, "end": 9, "reading": {"stress": [1]}}',
        '{"text": "замок", "start": 0, "end": 5, "form": "замки", "reading": {"stress": [1]}}',
        '{"text": "замок", "start": 0, "end": 5, "reading": {"stress": [7]}}',
        '{"text": "замок"}',
        "not json",
    ],
)
def test_bad_records_are_rejected(tmp_path: Path, line: str) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ExampleError, match=r"bad\.jsonl:1"):
        load_examples(path)


def test_evaluate_counts_and_reports() -> None:
    examples = [
        *parse_marked("В старом з+амке сломался зам+ок.", "a"),
        *parse_marked("Старого замк+а нет.", "b"),
        *parse_marked("Незнакомое сл+ово.", "c"),
    ]
    report = evaluate(examples, FakePack("ru"))
    assert (report.total, report.correct, report.unmarked) == (4, 2, 1)
    assert report.accuracy == 0.5
    assert report.model == "fake-0"
    assert [o.example.id for o in report.failures] == ["b", "c"]

    markdown = report.to_markdown()
    assert "| Correct | 2 (50.0%) |" in markdown
    assert "| Старого **замка** нет. | замк+а | з+амка |" in markdown
    assert "| Незнакомое **слово**. | сл+ово | слово (unmarked) |" in markdown
    assert report.to_dict()["failures"][1]["got"] == "слово (unmarked)"


def test_yo_and_single_vowel_words_are_judged_by_spelling() -> None:
    backend = ScriptedBackend({"все": "вс+ё"}, yo_homographs={"все": "всё"})
    pack = StressonnxPack("ru", backend=backend)
    examples = [*parse_marked("Он знал вс+ё."), *parse_marked("Вс+е пришли.")]
    report = evaluate(examples, pack)
    # The scripted backend restores ё every time: right in the first sentence, wrong in the second.
    assert [outcome.correct for outcome in report.outcomes] == [True, False]


def test_empty_evaluation() -> None:
    report = evaluate([], FakePack("ru"))
    assert (report.total, report.accuracy, report.chars_per_second) == (0, 0.0, 0.0)
    assert "Words tested | 0" in report.to_markdown()


def test_minimum_accuracy(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text('{"ru": {"min_accuracy": 0.8}, "uk": {}}', encoding="utf-8")
    assert minimum_accuracy(path, "ru") == 0.8
    assert minimum_accuracy(path, "uk") is None
    assert minimum_accuracy(path, "kk") is None
