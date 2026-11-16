"""Measure a language pack against sentences with known readings.

Two file formats are understood.

``.txt``: one sentence per line; the words under test carry a stress mark ("+" before the
stressed vowel or a combining acute after it); lines starting with "#" are comments::

    В старом з+амке сломался зам+ок.
    Он знал вс+ё.

A marked word written with ё is given to the pack with е instead, so the line also tests that ё
is restored.

``.jsonl``: one example record per line, as described in docs/DATA_SPEC.md.
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tonika.document import IntentDocumentError, Reading, Token
from tonika.packs import LanguagePack
from tonika.pipeline import analyze_with
from tonika.render import mark_stress
from tonika.text import count_vowels, lower, normalize, strip_author_marks


class ExampleError(ValueError):
    """Raised when an example file cannot be understood."""


@dataclass(frozen=True, slots=True)
class Example:
    """A word in a sentence and how it must be read."""

    text: str
    start: int
    end: int
    reading: Reading
    id: str = ""

    @property
    def form(self) -> str:
        return self.text[self.start : self.end]

    @property
    def surface(self) -> str:
        return self.reading.respell if self.reading.respell is not None else self.form


@dataclass(frozen=True, slots=True)
class Outcome:
    """What a pack said about one example. ``predicted`` is None when it said nothing."""

    example: Example
    predicted: Reading | None
    correct: bool


@dataclass(frozen=True, slots=True)
class EvalReport:
    lang: str
    model: str
    outcomes: tuple[Outcome, ...]
    seconds: float
    chars: int

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def correct(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.correct)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def unmarked(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.predicted is None)

    @property
    def chars_per_second(self) -> float:
        return self.chars / self.seconds if self.seconds > 0 else 0.0

    @property
    def failures(self) -> list[Outcome]:
        return [outcome for outcome in self.outcomes if not outcome.correct]

    def to_dict(self) -> dict[str, Any]:
        return {
            "lang": self.lang,
            "model": self.model,
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "unmarked": self.unmarked,
            "chars_per_second": round(self.chars_per_second, 1),
            "failures": [
                {
                    "id": outcome.example.id,
                    "text": outcome.example.text,
                    "word": outcome.example.form,
                    "expected": _show(outcome.example.form, outcome.example.reading),
                    "got": _show(outcome.example.form, outcome.predicted),
                }
                for outcome in self.failures
            ],
        }

    def to_markdown(self, max_failures: int = 60) -> str:
        lines = [
            f"### Tonika accuracy: `{self.lang}`",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Words tested | {self.total} |",
            f"| Correct | {self.correct} ({self.accuracy:.1%}) |",
            f"| Left unmarked by the pack | {self.unmarked} |",
            f"| Speed | {self.chars_per_second:,.0f} characters per second |",
            f"| Pack | `{self.model}` |",
        ]
        failures = self.failures
        if failures:
            lines += [
                "",
                f"<details><summary>Wrong readings: {len(failures)}</summary>",
                "",
                "| Sentence | Expected | Got |",
                "| --- | --- | --- |",
            ]
            for outcome in failures[:max_failures]:
                example = outcome.example
                before, after = example.text[: example.start], example.text[example.end :]
                sentence = f"{before}**{example.form}**{after}"
                lines.append(
                    f"| {sentence.replace('|', '/')} "
                    f"| {_show(example.form, example.reading)} "
                    f"| {_show(example.form, outcome.predicted)} |"
                )
            if len(failures) > max_failures:
                lines.append(f"| … and {len(failures) - max_failures} more | | |")
            lines += ["", "</details>"]
        return "\n".join(lines) + "\n"


def parse_marked(line: str, example_id: str = "") -> list[Example]:
    """Read one sentence in which the words under test carry a stress mark."""
    clean = strip_author_marks(normalize(line.strip()))
    chars = list(clean.text)
    for word in clean.author_words:
        for i in range(word.start, word.end):
            chars[i] = {"ё": "е", "Ё": "Е"}.get(chars[i], chars[i])
    source = "".join(chars)
    examples: list[Example] = []
    for number, word in enumerate(clean.author_words, 1):
        gold = clean.text[word.start : word.end]
        plain = source[word.start : word.end]
        reading = Reading(stress=word.stress, respell=None if gold == plain else gold)
        suffix = f".{number}" if len(clean.author_words) > 1 else ""
        examples.append(Example(source, word.start, word.end, reading, f"{example_id}{suffix}"))
    return examples


def load_examples(path: str | Path) -> list[Example]:
    """Load examples from a ``.txt`` or ``.jsonl`` file."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    examples: list[Example] = []
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{path}:{number}"
        if path.suffix == ".jsonl":
            examples.append(_from_record(line, where))
            continue
        found = parse_marked(line, f"{path.stem}:{number}")
        if not found:
            raise ExampleError(f"{where}: no word carries a stress mark")
        examples.extend(found)
    return examples


def evaluate(examples: Sequence[Example], pack: LanguagePack) -> EvalReport:
    """Run ``pack`` over ``examples`` and compare its readings with the expected ones."""
    by_text: dict[str, list[Example]] = {}
    for example in examples:
        by_text.setdefault(example.text, []).append(example)
    if by_text:
        # Load the models before the clock starts.
        pack.analyze(next(iter(by_text)))

    outcomes: list[Outcome] = []
    seconds = 0.0
    chars = 0
    for text, group in by_text.items():
        started = time.perf_counter()
        document = analyze_with(pack, text)
        seconds += time.perf_counter() - started
        chars += len(text)
        tokens = {(token.start, token.end): token for token in document.tokens}
        for example in group:
            token = tokens.get((example.start, example.end))
            outcomes.append(
                Outcome(example, None if token is None else token.reading, _matches(example, token))
            )
    return EvalReport(pack.lang, pack.model, tuple(outcomes), seconds, chars)


def minimum_accuracy(path: str | Path, lang: str) -> float | None:
    """Read the accuracy floor for ``lang`` from a baseline file, if it sets one."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entry = data.get(lang) if isinstance(data, dict) else None
    value = entry.get("min_accuracy") if isinstance(entry, dict) else None
    return float(value) if isinstance(value, int | float) else None


def _matches(example: Example, token: Token | None) -> bool:
    surface = example.form if token is None else token.surface
    if lower(surface) != lower(example.surface):
        return False
    if count_vowels(example.surface) <= 1:
        return True
    predicted = () if token is None else token.reading.stress[:1]
    return predicted == example.reading.stress[:1]


def _show(form: str, reading: Reading | None) -> str:
    if reading is None:
        return f"{form} (unmarked)"
    surface = reading.respell if reading.respell is not None else form
    return mark_stress(surface, reading.stress, "plus")


def _from_record(line: str, where: str) -> Example:
    try:
        data = json.loads(line)
        text = normalize(data["text"])
        start, end = int(data["start"]), int(data["end"])
        reading = Reading.from_dict(data["reading"])
    except (KeyError, TypeError, ValueError, IntentDocumentError) as exc:
        raise ExampleError(f"{where}: {exc}") from exc
    if not 0 <= start < end <= len(text):
        raise ExampleError(f"{where}: offsets {start}..{end} are outside the text")
    form = text[start:end]
    if "form" in data and data["form"] != form:
        raise ExampleError(f"{where}: form {data['form']!r} does not match the text")
    surface = reading.respell if reading.respell is not None else form
    if any(not 0 <= index < len(surface) for index in reading.stress):
        raise ExampleError(f"{where}: a stress index is outside {surface!r}")
    return Example(text, start, end, reading, str(data.get("id", "")))
