from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tonika import NOTATIONS

ENGINES = sorted((Path(__file__).parent.parent / "engines").glob("*.yaml"))
REQUIRED = {"id", "name", "notation", "languages", "notes", "verified_by", "verified_on",
            "source_url"}  # fmt: skip


def test_there_are_presets() -> None:
    assert ENGINES


@pytest.mark.parametrize("path", ENGINES, ids=lambda p: p.stem)
def test_preset_is_well_formed(path: Path) -> None:
    preset = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(preset) >= REQUIRED, f"missing: {REQUIRED - set(preset)}"
    assert preset["id"] == path.stem
    assert preset["notation"] in NOTATIONS
    assert isinstance(preset["languages"], list) and preset["languages"]
    if preset["verified_by"] != "unverified":
        assert preset["source_url"], "a verified preset needs a source"
