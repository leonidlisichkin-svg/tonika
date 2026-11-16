"""The interface every language pack implements."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from tonika.document import Token

Tier = Literal["A", "B", "C"]
"""How much a pack knows. A: resolves words by context and knows which are ambiguous.
B: dictionary or rule stress, no ambiguity. C: user dictionary only."""


class PackError(RuntimeError):
    """Raised when a language pack cannot load or run its models."""


@runtime_checkable
class LanguagePack(Protocol):
    """Turns clean, NFC-normalised text into tokens with pronunciation decisions.

    A pack returns tokens only for words it has an opinion about, with offsets into the text
    it was given. The pipeline removes the author's stress marks before calling the pack and
    applies the user dictionary after it, so a pack can stay small.
    """

    @property
    def lang(self) -> str:
        """BCP-47 language tag, e.g. ``"ru"``."""
        ...

    @property
    def model(self) -> str:
        """Model and data version, recorded in every Intent Document."""
        ...

    @property
    def tier(self) -> Tier:
        """Coverage tier of this pack."""
        ...

    @property
    def demo(self) -> bool:
        """True for packs that exist only for tests and demos."""
        ...

    def analyze(self, text: str) -> list[Token]:
        """Return pronunciation decisions for ``text``."""
        ...
