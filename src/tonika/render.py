"""Renderers: turn an Intent Document into text a TTS engine understands."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, get_args

from tonika.document import IntentDocument, Token
from tonika.text import COMBINING_ACUTE

Notation = Literal["acute", "plus", "upper", "yo"]
Mode = Literal["ambiguous", "all", "yo"]

NOTATIONS: tuple[str, ...] = get_args(Notation)
MODES: tuple[str, ...] = get_args(Mode)


def render(document: IntentDocument, target: str = "acute", mode: str = "ambiguous") -> str:
    """Render ``document`` in a notation.

    Notations: ``acute`` (за́мок), ``plus`` (з+амок), ``upper`` (зАмок), ``yo`` (respelling only).
    Modes: ``ambiguous`` marks only tokens with alternatives, ``all`` marks every token, ``yo``
    applies respelling only. Respelling (все → всё) is applied in every mode. Text outside
    tokens is copied unchanged, so the layout of the input survives.
    """
    if target not in NOTATIONS:
        raise ValueError(f"unknown notation {target!r}; choose from {', '.join(NOTATIONS)}")
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; choose from {', '.join(MODES)}")
    parts: list[str] = []
    position = 0
    for token in document.tokens:
        parts.append(document.text[position : token.start])
        parts.append(_render_token(token, target, mode))
        position = token.end
    parts.append(document.text[position:])
    return "".join(parts)


def mark_stress(word: str, indices: Iterable[int], notation: str) -> str:
    """Mark the letters at ``indices`` in ``word``."""
    wanted = set(indices)
    out: list[str] = []
    for i, char in enumerate(word):
        if i not in wanted:
            out.append(char)
        elif notation == "acute":
            out.append(char + COMBINING_ACUTE)
        elif notation == "plus":
            out.append("+" + char)
        elif notation == "upper":
            out.append(char.upper())
        else:
            raise ValueError(f"notation {notation!r} cannot mark stress")
    return "".join(out)


def _render_token(token: Token, target: str, mode: str) -> str:
    surface = token.surface
    if target == "yo" or mode == "yo" or not token.reading.stress:
        return surface
    if mode == "ambiguous" and not token.is_ambiguous:
        return surface
    return mark_stress(surface, token.reading.stress, target)
