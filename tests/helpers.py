"""Shared test helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import pytest

from tonika.render import mark_stress
from tonika.text import match_case, split_marks

PROOF_TEXT = "В старом замке сломался замок."

# The characters stressonnx 0.0.2 keeps when it normalises Russian text; it drops the rest.
_DROPPED_BY_RUACCENT = re.compile(r"[^a-zA-Z0-9\sа-яА-ЯёЁ—.,!?:;\"“”‘’(){}\[\]«»„\-]")


class ScriptedBackend:
    """Stands in for a stressonnx model: marks the words it was told about.

    ``readings`` maps a lowercase word to its marked form, written with "+" before the stressed
    vowel and with ё where it should be restored. ``lossy`` imitates stressonnx 0.0.2, which
    drops unusual characters and the space before punctuation.
    """

    def __init__(
        self,
        readings: Mapping[str, str],
        *,
        homographs: Mapping[str, Sequence[str]] | None = None,
        yo_homographs: Mapping[str, str] | None = None,
        lossy: bool = False,
    ) -> None:
        self.readings = dict(readings)
        self.lossy = lossy
        self.calls: list[str] = []
        if homographs is not None:
            self._omographs = dict(homographs)
        if yo_homographs is not None:
            self._yo_homographs = dict(yo_homographs)

    def __call__(self, text: str) -> str:
        self.calls.append(text)
        if self.lossy:
            text = _DROPPED_BY_RUACCENT.sub("", text)

        def mark(match: re.Match[str]) -> str:
            word = match.group()
            marked = self.readings.get(word.lower())
            if marked is None:
                return word
            letters, stress = split_marks(marked)
            return mark_stress(match_case(word, letters), stress, "acute")

        out = re.sub(r"[^\W\d_]+", mark, text)
        if self.lossy:
            out = re.sub(r" ([,.!?:;])", r"\1", out)
        return out


class FakeStressonnx:
    """Stands in for the stressonnx package: a registry, and a loader that counts its calls."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, delay: float = 0.0) -> None:
        import sys
        import time
        import types

        self.loads = 0
        registry = types.ModuleType("stressonnx.registry")
        registry.HF_REPO_REVISION = "b8ba7afdb78534afa1a7f4794b98d019c3866aef"  # type: ignore[attr-defined]
        registry.DEFAULT_MODEL = {"ru": "ruaccent", "uk": "silero"}  # type: ignore[attr-defined]
        package = types.ModuleType("stressonnx")
        package.registry = registry  # type: ignore[attr-defined]
        package.DEFAULT_MODEL = registry.DEFAULT_MODEL  # type: ignore[attr-defined]

        def make_stressor(model: str | None = None, lang: str | None = None) -> object:
            self.loads += 1
            time.sleep(delay)
            return lambda text: text

        package.make_stressor = make_stressor  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "stressonnx", package)
        monkeypatch.setitem(sys.modules, "stressonnx.registry", registry)
        monkeypatch.setattr("tonika.packs.stressonnx.metadata.version", lambda name: "0.0.2")
