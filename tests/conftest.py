from __future__ import annotations

import pytest

from helpers import PROOF_TEXT
from tonika import IntentDocument, analyze


@pytest.fixture(autouse=True)
def _no_real_packs(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline tests behave the same whether or not real language packs are installed."""
    if "models" not in request.keywords:
        monkeypatch.setattr("tonika.packs._stressonnx_languages", lambda: frozenset())


@pytest.fixture
def proof_document() -> IntentDocument:
    return analyze(PROOF_TEXT, lang="ru", pack="fake")
