"""Server settings, read once from the environment when the app is created."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """``pack``: the pack name every request uses; clients cannot choose it.
    ``max_chars``: the limit for ``text`` and for ``dictionary``, in code points after NFC.
    ``parallel``: analyses that may run at the same time; the rest wait.
    ``cors_origins``: origins allowed to call the API from a browser.
    """

    pack: str = "auto"
    max_chars: int = 20_000
    parallel: int = 1
    cors_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_chars < 1:
            raise ValueError("TONIKA_MAX_CHARS must be a positive whole number")
        if self.parallel < 1:
            raise ValueError("TONIKA_PARALLEL must be a positive whole number")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        origins = tuple(
            origin.strip()
            for origin in env.get("TONIKA_CORS_ORIGINS", "").split(",")
            if origin.strip()
        )
        return cls(
            pack=env.get("TONIKA_PACK", "auto").strip() or "auto",
            max_chars=_whole_number(env, "TONIKA_MAX_CHARS", 20_000),
            parallel=_whole_number(env, "TONIKA_PARALLEL", 1),
            cors_origins=origins,
        )


def _whole_number(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a positive whole number, not {raw!r}") from None
