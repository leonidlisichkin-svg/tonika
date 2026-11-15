"""The interface every language pack implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tonika.document import Token


@runtime_checkable
class LanguagePack(Protocol):
    """Turns NFC-normalised text into tokens with pronunciation decisions.

    A pack returns tokens only for words it has an opinion about, sorted by offset and with
    offsets into the text it was given. The pipeline handles normalisation, author marks and
    validation, so a pack can stay small.
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
    def demo(self) -> bool:
        """True for packs that exist only for tests and demos."""
        ...

    def analyze(self, text: str) -> list[Token]:
        """Return pronunciation decisions for ``text``."""
        ...
