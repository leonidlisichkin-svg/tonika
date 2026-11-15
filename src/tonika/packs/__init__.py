"""Language pack registry."""

from __future__ import annotations

import warnings

from tonika.packs.base import LanguagePack
from tonika.packs.fake import FakePack

__all__ = [
    "DemoPackWarning",
    "FakePack",
    "LanguagePack",
    "UnknownPackError",
    "available_packs",
    "get_pack",
]


class UnknownPackError(LookupError):
    """Raised when no pack exists for the requested language or name."""


class DemoPackWarning(UserWarning):
    """Emitted when "auto" falls back to the demo pack because no real pack is installed."""


def available_packs() -> dict[str, list[str]]:
    """Pack names per language."""
    return {lang: ["fake"] for lang in sorted(FakePack.languages)}


def get_pack(lang: str, name: str = "auto") -> LanguagePack:
    """Return a language pack.

    ``name="auto"`` picks the best installed pack. Until Phase 1 ships the real Russian pack,
    "auto" falls back to the demo pack and emits :class:`DemoPackWarning`.
    """
    if name not in {"auto", "fake"}:
        raise UnknownPackError(f"unknown pack {name!r}")
    if lang not in FakePack.languages:
        raise UnknownPackError(f"no language pack for {lang!r} yet")
    if name == "auto":
        warnings.warn(
            f"no real language pack for {lang!r} is installed yet; using the demo pack",
            DemoPackWarning,
            stacklevel=2,
        )
    return FakePack(lang)
