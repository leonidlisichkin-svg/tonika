"""TTS engine presets: which notation each engine honours.

Each preset is a TOML file next to this module, named after the engine id. Presets are data
(CC0-1.0) and anyone can verify or correct them; see CONTRIBUTING.md.
"""

from __future__ import annotations

import functools
import tomllib
from dataclasses import dataclass
from importlib import resources

from tonika.render import NOTATIONS


class UnknownEngineError(LookupError):
    """Raised when a target is neither a notation nor a known engine."""


@dataclass(frozen=True, slots=True)
class Engine:
    """How one TTS engine wants stress to be written.

    ``verified_by`` is ``"documentation"``, a person's handle, or ``"unverified"``.
    """

    id: str
    name: str
    notation: str
    languages: tuple[str, ...]
    notes: str
    verified_by: str
    verified_on: str
    source_url: str


@functools.cache
def _engines() -> dict[str, Engine]:
    engines: dict[str, Engine] = {}
    for item in resources.files(__package__).iterdir():
        if not item.name.endswith(".toml"):
            continue
        data = tomllib.loads(item.read_text(encoding="utf-8"))
        engine_id = item.name.removesuffix(".toml")
        notation = str(data["notation"])
        if notation not in NOTATIONS:
            raise ValueError(f"engine preset {engine_id!r} has unknown notation {notation!r}")
        engines[engine_id] = Engine(
            id=engine_id,
            name=str(data["name"]),
            notation=notation,
            languages=tuple(str(lang) for lang in data.get("languages", ["*"])),
            notes=" ".join(str(data.get("notes", "")).split()),
            verified_by=str(data.get("verified_by", "unverified")),
            verified_on=str(data.get("verified_on", "")),
            source_url=str(data.get("source_url", "")),
        )
    return dict(sorted(engines.items()))


def list_engines() -> list[Engine]:
    """All engine presets, sorted by id."""
    return list(_engines().values())


def get_engine(engine_id: str) -> Engine:
    try:
        return _engines()[engine_id]
    except KeyError:
        raise UnknownEngineError(
            f"unknown target {engine_id!r}; choose a notation ({', '.join(NOTATIONS)}) "
            f"or an engine ({', '.join(_engines())})"
        ) from None


def resolve_target(target: str) -> str:
    """Return the notation for ``target``, which is a notation name or an engine id."""
    if target in NOTATIONS:
        return target
    return get_engine(target).notation
