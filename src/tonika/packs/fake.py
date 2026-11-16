"""A deterministic demo pack with a tiny built-in table.

It exists so the core, the renderers and the CLI can be tested offline with no models. It does
not read context: every word always gets the same reading. Never use it for real voice-over.
"""

from __future__ import annotations

from dataclasses import dataclass

from tonika.document import Reading, Token, TokenKind
from tonika.packs.base import Tier
from tonika.text import iter_words, match_case


@dataclass(frozen=True, slots=True)
class _Entry:
    reading: Reading
    alternatives: tuple[Reading, ...] = ()
    kind: TokenKind = "stress"
    confidence: float = 1.0


_RU_TABLE: dict[str, _Entry] = {
    # Homographs. The demo pack always picks the same reading.
    "замок": _Entry(Reading(stress=(3,)), (Reading(stress=(1,)),), confidence=0.94),  # замо́к
    "замке": _Entry(Reading(stress=(1,)), (Reading(stress=(4,)),), confidence=0.97),  # за́мке
    "замка": _Entry(Reading(stress=(1,)), (Reading(stress=(4,)),), confidence=0.60),  # за́мка
    # Unambiguous words, so that mode "all" differs from mode "ambiguous".
    "старом": _Entry(Reading(stress=(2,))),  # ста́ром
    "сломался": _Entry(Reading(stress=(4,))),  # слома́лся
    "дверь": _Entry(Reading(stress=(2,))),  # две́рь
    # The letter ё.
    "еще": _Entry(Reading(stress=(2,), respell="ещё"), kind="yo"),
    "все": _Entry(
        Reading(stress=(2,), respell="всё"),
        (Reading(stress=(2,)),),
        kind="yo",
        confidence=0.55,
    ),
}

_TABLES: dict[str, dict[str, _Entry]] = {"ru": _RU_TABLE}


class FakePack:
    """Demo language pack. See the module docstring."""

    languages: frozenset[str] = frozenset(_TABLES)

    def __init__(self, lang: str = "ru") -> None:
        if lang not in _TABLES:
            raise ValueError(f"the demo pack has no table for {lang!r}")
        self._lang = lang
        self._table = _TABLES[lang]

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def model(self) -> str:
        return "fake-0"

    @property
    def tier(self) -> Tier:
        return "A"

    @property
    def demo(self) -> bool:
        return True

    def analyze(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        for start, end, word in iter_words(text):
            entry = self._table.get(word.lower())
            if entry is None:
                continue
            reading = entry.reading
            if reading.respell is not None:
                reading = Reading(
                    stress=reading.stress,
                    respell=match_case(word, reading.respell),
                    ipa=reading.ipa,
                    reading_id=reading.reading_id,
                )
            tokens.append(
                Token(
                    start=start,
                    end=end,
                    form=word,
                    reading=reading,
                    kind=entry.kind,
                    alternatives=entry.alternatives,
                    confidence=entry.confidence,
                    source="lexicon",
                )
            )
        return tokens
