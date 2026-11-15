from __future__ import annotations

import pytest

from tonika import IntentDocument, analyze

PROOF_TEXT = "В старом замке сломался замок."


@pytest.fixture
def proof_document() -> IntentDocument:
    return analyze(PROOF_TEXT, lang="ru", pack="fake")
