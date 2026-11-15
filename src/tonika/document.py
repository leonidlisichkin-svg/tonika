"""The Intent Document: what Tonika decided about pronunciation, separate from how it is shown.

Analysis produces an :class:`IntentDocument`. Renderers turn it into text for a TTS engine.
Offsets are code-point indices into ``text`` after NFC normalisation.
"""

from __future__ import annotations

import json
import math
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast, get_args

SPEC_VERSION = "1.0"

TokenKind = Literal["stress", "yo", "heteronym", "polyphone", "diacritics", "custom"]
Source = Literal["model", "lexicon", "rules", "user", "input"]

TOKEN_KINDS: frozenset[str] = frozenset(get_args(TokenKind))
SOURCES: frozenset[str] = frozenset(get_args(Source))

_READING_KEYS = frozenset({"stress", "respell", "ipa", "reading_id"})
_TOKEN_KEYS = frozenset(
    {"start", "end", "form", "kind", "reading", "alternatives", "confidence", "source"}
)
_DOCUMENT_KEYS = frozenset({"spec", "lang", "model", "text", "tokens"})


class IntentDocumentError(ValueError):
    """Raised when an Intent Document is malformed."""


@dataclass(frozen=True, slots=True)
class Reading:
    """One way to pronounce a token.

    ``stress`` holds zero-based letter indices into the token's surface form: the ``respell``
    when it is set, otherwise the original form. The first index is the primary stress.
    An empty reading means "read as written".
    """

    stress: tuple[int, ...] = ()
    respell: str | None = None
    ipa: str | None = None
    reading_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.stress:
            out["stress"] = list(self.stress)
        if self.respell is not None:
            out["respell"] = self.respell
        if self.ipa is not None:
            out["ipa"] = self.ipa
        if self.reading_id is not None:
            out["reading_id"] = self.reading_id
        return out

    @classmethod
    def from_dict(cls, data: Any) -> Reading:
        if not isinstance(data, Mapping):
            raise IntentDocumentError("a reading must be an object")
        unknown = set(data) - _READING_KEYS
        if unknown:
            raise IntentDocumentError(f"unknown reading fields: {sorted(unknown)}")
        stress = data.get("stress", [])
        if not isinstance(stress, list) or not all(_is_int(i) for i in stress):
            raise IntentDocumentError("reading.stress must be a list of integers")
        for key in ("respell", "ipa", "reading_id"):
            value = data.get(key)
            if value is not None and not isinstance(value, str):
                raise IntentDocumentError(f"reading.{key} must be a string")
        return cls(
            stress=tuple(stress),
            respell=data.get("respell"),
            ipa=data.get("ipa"),
            reading_id=data.get("reading_id"),
        )


@dataclass(frozen=True, slots=True)
class Token:
    """A span of the input whose pronunciation Tonika has an opinion about.

    ``confidence`` is between 0 and 1, or ``None`` when the source cannot estimate it.
    """

    start: int
    end: int
    form: str
    reading: Reading
    kind: TokenKind = "stress"
    alternatives: tuple[Reading, ...] = ()
    confidence: float | None = None
    source: Source = "model"

    @property
    def is_ambiguous(self) -> bool:
        """True when the token could be read another way."""
        return bool(self.alternatives)

    @property
    def surface(self) -> str:
        """The form after respelling, which stress indices refer to."""
        return self.reading.respell if self.reading.respell is not None else self.form

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "start": self.start,
            "end": self.end,
            "form": self.form,
            "kind": self.kind,
            "reading": self.reading.to_dict(),
        }
        if self.alternatives:
            out["alternatives"] = [alt.to_dict() for alt in self.alternatives]
        if self.confidence is not None:
            out["confidence"] = self.confidence
        out["source"] = self.source
        return out

    @classmethod
    def from_dict(cls, data: Any) -> Token:
        if not isinstance(data, Mapping):
            raise IntentDocumentError("a token must be an object")
        unknown = set(data) - _TOKEN_KEYS
        if unknown:
            raise IntentDocumentError(f"unknown token fields: {sorted(unknown)}")
        for key in ("start", "end", "form", "reading"):
            if key not in data:
                raise IntentDocumentError(f"token is missing '{key}'")
        if not _is_int(data["start"]) or not _is_int(data["end"]):
            raise IntentDocumentError("token start and end must be integers")
        if not isinstance(data["form"], str):
            raise IntentDocumentError("token form must be a string")
        alternatives = data.get("alternatives", [])
        if not isinstance(alternatives, list):
            raise IntentDocumentError("token alternatives must be a list")
        confidence = data.get("confidence")
        if confidence is not None and (
            not isinstance(confidence, int | float) or isinstance(confidence, bool)
        ):
            raise IntentDocumentError("token confidence must be a number")
        kind = data.get("kind", "stress")
        source = data.get("source", "model")
        if kind not in TOKEN_KINDS:
            raise IntentDocumentError(f"unknown token kind: {kind!r}")
        if source not in SOURCES:
            raise IntentDocumentError(f"unknown token source: {source!r}")
        return cls(
            start=data["start"],
            end=data["end"],
            form=data["form"],
            reading=Reading.from_dict(data["reading"]),
            kind=cast(TokenKind, kind),
            alternatives=tuple(Reading.from_dict(alt) for alt in alternatives),
            confidence=None if confidence is None else float(confidence),
            source=cast(Source, source),
        )


@dataclass(frozen=True, slots=True)
class IntentDocument:
    """Text plus Tonika's pronunciation decisions about it. Validated on construction."""

    lang: str
    model: str
    text: str
    tokens: tuple[Token, ...] = ()
    spec: str = SPEC_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.spec != SPEC_VERSION:
            raise IntentDocumentError(f"unsupported spec version: {self.spec!r}")
        if not self.lang:
            raise IntentDocumentError("lang must not be empty")
        if not self.model:
            raise IntentDocumentError("model must not be empty")
        if unicodedata.normalize("NFC", self.text) != self.text:
            raise IntentDocumentError("text must be NFC-normalised")
        previous_end = 0
        for i, token in enumerate(self.tokens):
            where = f"token {i}"
            if not 0 <= token.start < token.end <= len(self.text):
                raise IntentDocumentError(
                    f"{where}: offsets {token.start}..{token.end} are invalid"
                )
            if token.start < previous_end:
                raise IntentDocumentError(f"{where}: tokens must be sorted and must not overlap")
            if self.text[token.start : token.end] != token.form:
                raise IntentDocumentError(
                    f"{where}: form {token.form!r} does not match the text at its offsets"
                )
            if token.kind not in TOKEN_KINDS:
                raise IntentDocumentError(f"{where}: unknown kind {token.kind!r}")
            if token.source not in SOURCES:
                raise IntentDocumentError(f"{where}: unknown source {token.source!r}")
            if token.confidence is not None and not (
                math.isfinite(token.confidence) and 0.0 <= token.confidence <= 1.0
            ):
                raise IntentDocumentError(f"{where}: confidence must be between 0 and 1")
            for reading in (token.reading, *token.alternatives):
                _check_reading(reading, token, where)
            previous_end = token.end

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec,
            "lang": self.lang,
            "model": self.model,
            "text": self.text,
            "tokens": [token.to_dict() for token in self.tokens],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: Any) -> IntentDocument:
        if not isinstance(data, Mapping):
            raise IntentDocumentError("an intent document must be an object")
        unknown = set(data) - _DOCUMENT_KEYS
        if unknown:
            raise IntentDocumentError(f"unknown document fields: {sorted(unknown)}")
        for key in ("spec", "lang", "model", "text"):
            if not isinstance(data.get(key), str):
                raise IntentDocumentError(f"document field '{key}' must be a string")
        tokens = data.get("tokens", [])
        if not isinstance(tokens, list):
            raise IntentDocumentError("document tokens must be a list")
        return cls(
            spec=data["spec"],
            lang=data["lang"],
            model=data["model"],
            text=data["text"],
            tokens=tuple(Token.from_dict(token) for token in tokens),
        )

    @classmethod
    def from_json(cls, raw: str) -> IntentDocument:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IntentDocumentError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(data)


def _check_reading(reading: Reading, token: Token, where: str) -> None:
    surface = reading.respell if reading.respell is not None else token.form
    if not surface:
        raise IntentDocumentError(f"{where}: respell must not be empty")
    if len(set(reading.stress)) != len(reading.stress):
        raise IntentDocumentError(f"{where}: stress indices must be unique")
    for index in reading.stress:
        if not 0 <= index < len(surface):
            raise IntentDocumentError(f"{where}: stress index {index} is outside {surface!r}")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
