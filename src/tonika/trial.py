"""Long-text trial: run a whole text through Tonika and prove only pronunciation changed.

A trial analyses the text once, renders it in every notation and every mode, and undoes each
rendering with the Intent Document alone: the marks at the stressed letters it records, and the
respellings it records. The result must be the input, character for character. The report also
records the load a human would face (words to review), what the run cost (speed, memory), the
processor it ran on and a digest of every decision, so a change of output across machines shows.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tonika.document import IntentDocument, Token
from tonika.packs import LanguagePack
from tonika.pipeline import analyze_with
from tonika.render import MODES, NOTATIONS, render
from tonika.text import COMBINING_ACUTE, PLUS, iter_words, split_marks

_CONTEXT = 20

DRIFT_LIMIT = 0.001
"""The largest share of words given stress by which a run may differ from its reference."""


@dataclass(frozen=True, slots=True)
class Reference:
    """What a trial gave on a reference machine, to measure drift on another one."""

    model: str
    digest: str
    words_marked: int
    machine: str = ""
    date: str = ""


def load_reference(path: str | Path, name: str) -> Reference | None:
    """Read the reference for the trial text ``name`` from a JSON file, if it has one."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entry = data.get(name) if isinstance(data, dict) else None
    if not isinstance(entry, dict):
        return None
    return Reference(
        model=str(entry["model"]),
        digest=str(entry["digest"]),
        words_marked=int(entry["words_marked"]),
        machine=str(entry.get("machine", "")),
        date=str(entry.get("date", "")),
    )


@dataclass(frozen=True, slots=True)
class Difference:
    """Where a rendering, once its marks are undone, first departs from the input."""

    notation: str
    mode: str
    position: int
    """Code-point index into the input."""
    expected: str
    """The input from ``position`` on, a few characters long."""
    got: str
    """The restored rendering from ``position`` on, a few characters long."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "notation": self.notation,
            "mode": self.mode,
            "position": self.position,
            "expected": self.expected,
            "got": self.got,
        }


@dataclass(frozen=True, slots=True)
class TrialReport:
    """What one long text cost and whether it came through intact."""

    name: str
    lang: str
    model: str
    characters: int
    words: int
    words_marked: int
    """Words that carry a stress decision: what ``--mode all`` marks."""
    words_to_review: int
    """Words with more than one reading: what ``--review`` lists."""
    yo_respellings: int
    """Words in which е was respelled as ё."""
    seconds: float
    """Time spent analysing the text, after the models were loaded."""
    peak_memory: int | None
    """Peak resident memory of the process in bytes, or None where it cannot be read."""
    checked: tuple[tuple[str, str], ...]
    """The (notation, mode) pairs that were rendered and undone."""
    difference: Difference | None
    digest: str
    """SHA-256 of the Intent Document's tokens: equal digests mean equal decisions."""
    cpu: str
    """The processor as the operating system names it, or "unknown"."""
    isa: str
    """The instruction set level the processor offers, such as "x86-64-v3", or "unknown"."""
    reference: Reference | None = None
    """The run to compare with; used only when it names the same model."""
    document: IntentDocument | None = field(default=None, repr=False, compare=False)
    """The Intent Document the trial checked; not part of the report itself."""

    @property
    def compared(self) -> bool:
        """True when a reference for the same model was given."""
        return self.reference is not None and self.reference.model == self.model

    @property
    def drift(self) -> float | None:
        """How far words given stress differ from the reference, as a share of its count.

        A net difference: a word gained and another lost cancel out. The digest tells whether
        anything differs at all.
        """
        if self.reference is None or not self.compared:
            return None
        expected = self.reference.words_marked
        return abs(self.words_marked - expected) / expected if expected else 0.0

    @property
    def within_drift_limit(self) -> bool:
        return self.drift is None or self.drift <= DRIFT_LIMIT

    @property
    def passed(self) -> bool:
        """Preserved, and no further from the reference than the drift limit allows."""
        return self.preserved and self.within_drift_limit

    @property
    def preserved(self) -> bool:
        return self.difference is None

    @property
    def first_difference(self) -> int | None:
        return None if self.difference is None else self.difference.position

    @property
    def review_per_1000_words(self) -> float:
        return 1000 * self.words_to_review / self.words if self.words else 0.0

    @property
    def chars_per_second(self) -> float:
        return self.characters / self.seconds if self.seconds > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lang": self.lang,
            "model": self.model,
            "characters": self.characters,
            "words": self.words,
            "words_marked": self.words_marked,
            "words_to_review": self.words_to_review,
            "review_per_1000_words": round(self.review_per_1000_words, 1),
            "yo_respellings": self.yo_respellings,
            "seconds": round(self.seconds, 3),
            "chars_per_second": round(self.chars_per_second, 1),
            "peak_memory_bytes": self.peak_memory,
            "checked": [f"{notation}/{mode}" for notation, mode in self.checked],
            "preserved": self.preserved,
            "first_difference": self.first_difference,
            "difference": None if self.difference is None else self.difference.to_dict(),
            "digest": self.digest,
            "cpu": self.cpu,
            "isa": self.isa,
            "reference_digest": None if self.reference is None else self.reference.digest,
            "same_as_reference": None
            if not self.compared or self.reference is None
            else self.digest == self.reference.digest,
            "drift": None if self.drift is None else round(self.drift, 6),
            "drift_limit": DRIFT_LIMIT,
            "passed": self.passed,
        }

    def to_markdown(self) -> str:
        title = f"`{self.name}`" if self.name else f"`{self.lang}`"
        share = self.words_marked / self.words if self.words else 0.0
        memory = (
            "not measured on this system"
            if self.peak_memory is None
            else f"{self.peak_memory / 2**20:,.0f} MiB (whole process)"
        )
        notations = sorted({notation for notation, _ in self.checked})
        modes = sorted({mode for _, mode in self.checked})
        combos = f"{len(notations)} notations × {len(modes)} modes"
        if self.difference is None:
            preserved = f"yes, in all {combos}"
        else:
            d = self.difference
            preserved = (
                f"**NO**: `{d.notation}` / `{d.mode}` differs at character {d.position:,}: "
                f"expected `{_code(d.expected)}`, got `{_code(d.got)}`"
            )
        lines = [
            f"### Tonika trial: {title}",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Text preserved | {preserved} |",
            f"| Characters | {self.characters:,} |",
            f"| Words | {self.words:,} |",
            f"| Words given stress (marked by `--mode all`) | {self.words_marked:,} "
            f"({share:.1%}) |",
            f"| Words with more than one reading (listed by `--review`) | "
            f"{self.words_to_review:,}: {self.review_per_1000_words:.1f} per 1,000 words |",
            f"| ё restored | {self.yo_respellings:,} |",
            f"| Speed | {self.chars_per_second:,.0f} characters per second |",
            f"| Peak memory | {memory} |",
            f"| Pack | `{self.model}` |",
            f"| Processor | {self.cpu}, {self.isa} |",
            f"| Digest of the decisions | `{self.digest}` |",
            *self._reference_rows(),
        ]
        return "\n".join(lines) + "\n"

    def _reference_rows(self) -> list[str]:
        reference = self.reference
        if reference is None:
            return []
        where = ", ".join(part for part in (reference.machine, reference.date) if part)
        label = f"| Against the reference ({where}) |" if where else "| Against the reference |"
        if not self.compared:
            return [f"{label} not compared: it is for `{reference.model}` |"]
        if self.digest == reference.digest:
            return [f"{label} the same decisions (digests match) |"]
        delta = self.words_marked - reference.words_marked
        verdict = "within" if self.within_drift_limit else "**OVER**"
        drift = self.drift or 0.0
        return [
            f"{label} decisions differ: {delta:+,} words given stress ({drift:.3%}), "
            f"{verdict} the limit of {DRIFT_LIMIT:.1%} |"
        ]


def run_trial(
    text: str,
    pack: LanguagePack,
    *,
    name: str = "",
    notations: Sequence[str] = NOTATIONS,
    modes: Sequence[str] = MODES,
    reference: Reference | None = None,
) -> TrialReport:
    """Analyse ``text`` with ``pack`` once and check every rendering of it.

    ``text`` is compared exactly as given: a text that is not NFC counts as changed, because
    Tonika's output is always NFC.
    """
    if text:
        # Load the models before the clock starts.
        pack.analyze(text[:200])
    started = time.perf_counter()
    document = analyze_with(pack, text)
    seconds = time.perf_counter() - started

    cpu, isa = processor()
    checked = tuple((notation, mode) for notation in notations for mode in modes)
    difference = check_preserved(text, document, checked)
    return TrialReport(
        name=name,
        lang=document.lang,
        model=document.model,
        characters=len(text),
        words=sum(1 for _ in iter_words(document.text)),
        words_marked=sum(1 for token in document.tokens if token.reading.stress),
        words_to_review=sum(1 for token in document.tokens if token.is_ambiguous),
        yo_respellings=sum(1 for token in document.tokens if _is_yo_respelling(token)),
        seconds=seconds,
        peak_memory=_peak_memory(),
        checked=checked,
        difference=difference,
        digest=token_digest(document),
        cpu=cpu,
        isa=isa,
        reference=reference,
        document=document,
    )


def token_digest(document: IntentDocument) -> str:
    """SHA-256 of the document's tokens as compact JSON with sorted keys.

    It covers the decisions only: not the text, the model string or any timing. Two machines
    that decide every word alike give the same digest.
    """
    payload = json.dumps(
        [token.to_dict() for token in document.tokens],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def processor() -> tuple[str, str]:
    """Name the processor and its instruction set level, from ``/proc/cpuinfo`` on Linux."""
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as handle:
            info = handle.read()
    except OSError:
        return "unknown", "unknown"
    return parse_cpuinfo(info, platform.machine())


# The x86-64 microarchitecture levels, as the Linux kernel spells the flags they require.
_X86_LEVELS: tuple[tuple[str, frozenset[str]], ...] = (
    ("x86-64-v2", frozenset({"cx16", "lahf_lm", "popcnt", "sse4_1", "sse4_2", "ssse3"})),
    (
        "x86-64-v3",
        frozenset({"avx", "avx2", "bmi1", "bmi2", "f16c", "fma", "abm", "movbe", "xsave"}),
    ),
    ("x86-64-v4", frozenset({"avx512f", "avx512bw", "avx512cd", "avx512dq", "avx512vl"})),
)
# Extensions that change which arithmetic kernels onnxruntime picks.
_X86_EXTRAS = ("avx512_vnni", "avx512_bf16", "avx_vnni", "amx_tile")
_ARM_EXTRAS = ("sve", "sve2", "bf16", "i8mm")


def parse_cpuinfo(info: str, machine: str = "") -> tuple[str, str]:
    """Read the processor name and instruction set level from the text of ``/proc/cpuinfo``."""
    fields: dict[str, str] = {}
    for line in info.splitlines():
        key, colon, value = line.partition(":")
        key = key.strip().lower()
        if colon and key not in fields:
            fields[key] = value.strip()
    name = fields.get("model name") or fields.get("hardware") or "unknown"
    if "flags" in fields:
        flags = set(fields["flags"].split())
        level = "x86-64"
        for candidate, required in _X86_LEVELS:
            if not required <= flags:
                break
            level = candidate
        extras = [flag for flag in _X86_EXTRAS if flag in flags]
    elif "features" in fields:
        flags = set(fields["features"].split())
        level = machine or "arm"
        extras = [flag for flag in _ARM_EXTRAS if flag in flags]
    else:
        return name, "unknown"
    return name, level + (f" ({', '.join(extras)})" if extras else "")


def check_preserved(
    text: str,
    document: IntentDocument,
    combinations: Sequence[tuple[str, str]] | None = None,
) -> Difference | None:
    """Render ``document`` in each (notation, mode), undo it, and compare with ``text``.

    Returns the first difference found, or None when every rendering gives ``text`` back.
    """
    if combinations is None:
        combinations = [(notation, mode) for notation in NOTATIONS for mode in MODES]
    for notation, mode in combinations:
        restored = restore(document, render(document, notation, mode), notation)
        position = _first_difference(text, restored)
        if position is not None:
            return Difference(
                notation=notation,
                mode=mode,
                position=position,
                expected=text[position : position + _CONTEXT],
                got=restored[position : position + _CONTEXT],
            )
    return None


def restore(document: IntentDocument, output: str, notation: str) -> str:
    """Undo a rendering of ``document`` in ``notation``, using only what the document records.

    Text between tokens is taken from ``output`` as it stands. At each token, ``output`` may
    hold the token's surface with a mark of ``notation`` at any of the letters the reading
    stresses, or the token's form exactly as typed; either is replaced by the form. Anything
    else is left as it stands, so the comparison with the input points at it.
    """
    parts: list[str] = []
    cursor = 0
    position = 0
    for token in document.tokens:
        gap = token.start - position
        parts.append(output[cursor : cursor + gap])
        cursor += gap
        match = _rendered_token(token, notation).match(output, cursor)
        if match is None:
            parts.append(output[cursor:])
            return "".join(parts)
        parts.append(token.form)
        cursor = match.end()
        position = token.end
    parts.append(output[cursor:])
    return "".join(parts)


def _rendered_token(token: Token, notation: str) -> re.Pattern[str]:
    stressed = set(token.reading.stress)
    pieces: list[str] = []
    for i, char in enumerate(token.surface):
        letter = re.escape(char)
        if i not in stressed or notation == "yo":
            pieces.append(letter)
        elif notation == "acute":
            pieces.append(f"{letter}{COMBINING_ACUTE}?")
        elif notation == "plus":
            pieces.append(f"{re.escape(PLUS)}?{letter}")
        elif notation == "upper":
            pieces.append(f"(?:{letter}|{re.escape(char.upper())})")
        else:
            raise ValueError(f"unknown notation {notation!r}")
    return re.compile(f"(?:{''.join(pieces)})|(?:{re.escape(token.form)})")


def _is_yo_respelling(token: Token) -> bool:
    """True when the reading turns an е of the typed word into ё."""
    respell = token.reading.respell
    return respell is not None and _yo_count(respell) > _yo_count(split_marks(token.form)[0])


def _yo_count(word: str) -> int:
    return sum(1 for char in word if char in "ёЁ")


def _first_difference(a: str, b: str) -> int | None:
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def _code(snippet: str) -> str:
    return snippet.replace("\n", "⏎").replace("`", "'").replace("|", "/")


def _peak_memory() -> int | None:
    try:
        import resource
    except ImportError:  # Windows
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kibibytes, macOS bytes.
    return int(peak) if sys.platform == "darwin" else int(peak) * 1024
