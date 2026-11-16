from __future__ import annotations

import pytest

from tonika import NOTATIONS
from tonika.engines import UnknownEngineError, get_engine, list_engines, resolve_target


def test_presets_are_well_formed() -> None:
    engines = list_engines()
    assert {engine.id for engine in engines} >= {
        "generic-acute",
        "generic-upper",
        "silero",
        "yandex-speechkit",
    }
    for engine in engines:
        assert engine.name and engine.notes
        assert engine.notation in NOTATIONS
        assert engine.languages
        if engine.verified_by != "unverified":
            assert engine.source_url, f"{engine.id}: a verified preset needs a source"
            assert engine.verified_on, f"{engine.id}: a verified preset needs a date"


def test_resolve_target() -> None:
    assert resolve_target("plus") == "plus"
    assert resolve_target("yandex-speechkit") == "plus"
    assert get_engine("generic-upper").notation == "upper"
    with pytest.raises(UnknownEngineError, match="choose a notation"):
        resolve_target("unknown-engine")
