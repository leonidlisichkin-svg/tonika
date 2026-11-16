from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from tonika import IntentDocument, IntentDocumentError, Reading, Token

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "spec" / "intent-document.schema.json").read_text("utf-8")
)

TEXT = "В старом замке сломался замок."


def make(tokens: tuple[Token, ...], text: str = TEXT) -> IntentDocument:
    return IntentDocument(lang="ru", model="test", text=text, tokens=tokens)


def lock(**overrides: Any) -> Token:
    fields: dict[str, Any] = {
        "start": 24,
        "end": 29,
        "form": "замок",
        "reading": Reading(stress=(3,)),
        "alternatives": (Reading(stress=(1,)),),
        "confidence": 0.94,
    }
    fields.update(overrides)
    return Token(**fields)


def test_valid_document_round_trips_through_json() -> None:
    document = make((lock(),))
    assert IntentDocument.from_json(document.to_json()) == document


def test_document_matches_schema(proof_document: IntentDocument) -> None:
    jsonschema.validate(proof_document.to_dict(), SCHEMA)


def test_schema_rejects_unknown_kind() -> None:
    data = make((lock(),)).to_dict()
    data["tokens"][0]["kind"] = "accent"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, SCHEMA)


def test_spec_example_from_the_docs_is_valid() -> None:
    raw = {
        "spec": "1.0",
        "lang": "ru",
        "model": "fake-0",
        "text": TEXT,
        "tokens": [
            {"start": 9, "end": 14, "form": "замке", "kind": "stress",
             "reading": {"stress": [1]}, "alternatives": [{"stress": [4]}],
             "confidence": 0.97, "source": "model"},
            {"start": 24, "end": 29, "form": "замок", "kind": "stress",
             "reading": {"stress": [3]}, "alternatives": [{"stress": [1]}],
             "confidence": 0.94, "source": "model"},
        ],
    }  # fmt: skip
    jsonschema.validate(raw, SCHEMA)
    assert len(IntentDocument.from_dict(raw).tokens) == 2


def test_confidence_is_optional() -> None:
    document = make((lock(confidence=None),))
    assert "confidence" not in document.to_dict()["tokens"][0]
    assert IntentDocument.from_json(document.to_json()) == document
    jsonschema.validate(document.to_dict(), SCHEMA)


def test_token_properties() -> None:
    token = lock()
    assert token.is_ambiguous
    assert token.surface == "замок"
    yo = Token(start=0, end=3, form="все", reading=Reading(stress=(2,), respell="всё"), kind="yo")
    assert yo.surface == "всё"
    assert not yo.is_ambiguous


@pytest.mark.parametrize(
    ("token", "message"),
    [
        (lock(start=24, end=40), "offsets"),
        (lock(start=23, end=28), "does not match"),
        (lock(form="замак"), "does not match"),
        (lock(reading=Reading(stress=(5,))), "outside"),
        (lock(reading=Reading(stress=(1, 1))), "unique"),
        (lock(confidence=1.5), "confidence"),
        (lock(confidence=float("nan")), "confidence"),
        (lock(kind="accent"), "kind"),
        (lock(source="guess"), "source"),
    ],
)
def test_invalid_tokens_are_rejected(token: Token, message: str) -> None:
    with pytest.raises(IntentDocumentError, match=message):
        make((token,))


def test_tokens_must_be_sorted_and_not_overlap() -> None:
    castle = Token(start=9, end=14, form="замке", reading=Reading(stress=(1,)))
    with pytest.raises(IntentDocumentError, match="sorted"):
        make((lock(), castle))


def test_text_must_be_nfc() -> None:
    decomposed = "й"  # и + combining breve; NFC composes it to й
    with pytest.raises(IntentDocumentError, match="NFC"):
        make((), text=decomposed)


def test_document_fields_are_checked() -> None:
    with pytest.raises(IntentDocumentError, match="lang"):
        IntentDocument(lang="", model="m", text="x")
    with pytest.raises(IntentDocumentError, match="spec"):
        IntentDocument(lang="ru", model="m", text="x", spec="2.0")


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        "{not json",
        '{"spec": "1.0", "lang": "ru", "model": "m", "text": "x", "extra": 1}',
        '{"spec": "1.0", "lang": "ru", "model": "m", "text": "x", "tokens": [{"start": 0}]}',
        '{"spec": "1.0", "lang": "ru", "model": "m", "text": "x",'
        ' "tokens": [{"start": 0, "end": 1, "form": "x", "reading": {"stress": ["0"]}}]}',
    ],
)
def test_malformed_json_is_rejected(raw: str) -> None:
    with pytest.raises(IntentDocumentError):
        IntentDocument.from_json(raw)
