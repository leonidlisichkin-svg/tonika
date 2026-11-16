"""Language pack registry."""

from __future__ import annotations

import functools
import threading
import warnings

from tonika.packs.base import LanguagePack, PackError, Tier
from tonika.packs.fake import FakePack
from tonika.packs.stressonnx import StressonnxPack

__all__ = [
    "DemoPackWarning",
    "FakePack",
    "LanguagePack",
    "PackError",
    "StressonnxPack",
    "Tier",
    "UnknownPackError",
    "available_packs",
    "get_pack",
]

_INSTALL_HINT = "install it with: pip install 'tonika[ru]'"

# Real packs hold loaded models, so each is built once per process.
_INSTANCES: dict[tuple[str, str | None], StressonnxPack] = {}
_INSTANCES_LOCK = threading.Lock()


class UnknownPackError(LookupError):
    """Raised when no pack exists for the requested language or name."""


class DemoPackWarning(UserWarning):
    """Emitted when "auto" falls back to the demo pack because no real pack is installed."""


@functools.cache
def _stressonnx_languages() -> frozenset[str]:
    try:
        import stressonnx
    except ImportError:
        return frozenset()
    return frozenset(str(lang) for lang in stressonnx.ALL_LANGS)


def _stressonnx(lang: str, model: str | None) -> StressonnxPack:
    key = (lang, model)
    with _INSTANCES_LOCK:
        if key not in _INSTANCES:
            _INSTANCES[key] = StressonnxPack(lang, model)
        return _INSTANCES[key]


def available_packs() -> dict[str, list[str]]:
    """Pack names per language, best first."""
    packs: dict[str, list[str]] = {lang: ["stressonnx"] for lang in _stressonnx_languages()}
    for lang in FakePack.languages:
        packs.setdefault(lang, []).append("fake")
    return dict(sorted(packs.items()))


def get_pack(lang: str, name: str = "auto") -> LanguagePack:
    """Return a language pack.

    Names: ``"auto"`` picks the best installed pack; ``"stressonnx"`` or
    ``"stressonnx:<model id>"`` asks for a stressonnx model; ``"fake"`` is the demo pack.
    When no real pack is installed, "auto" falls back to the demo pack for the languages it
    covers and emits :class:`DemoPackWarning`.
    """
    if name == "fake":
        if lang not in FakePack.languages:
            raise UnknownPackError(f"the demo pack has no table for {lang!r}")
        return FakePack(lang)

    if name == "auto":
        if lang in _stressonnx_languages():
            return _stressonnx(lang, None)
        if lang in FakePack.languages:
            warnings.warn(
                f"no real language pack for {lang!r} is installed; using the demo pack "
                f"({_INSTALL_HINT})",
                DemoPackWarning,
                stacklevel=2,
            )
            return FakePack(lang)
        raise UnknownPackError(f"no language pack for {lang!r}")

    if name == "stressonnx" or name.startswith("stressonnx:"):
        languages = _stressonnx_languages()
        if not languages:
            raise UnknownPackError(f"the stressonnx pack is not installed; {_INSTALL_HINT}")
        if lang not in languages:
            raise UnknownPackError(f"stressonnx has no model for {lang!r}")
        return _stressonnx(lang, name.partition(":")[2] or None)

    raise UnknownPackError(f"unknown pack {name!r}")
