"""The public entry points: analyse text, then render it."""

from __future__ import annotations

from tonika.document import IntentDocument, Token
from tonika.packs import get_pack
from tonika.render import render
from tonika.text import normalize, protected_spans


def analyze(text: str, lang: str = "ru", pack: str = "auto") -> IntentDocument:
    """Return an Intent Document for ``text``.

    The text is NFC-normalised first; all offsets refer to the normalised text. Words the author
    already marked with an acute or a plus are left out, so the renderer copies them as typed.
    """
    normalised = normalize(text)
    language_pack = get_pack(lang, pack)
    protected = protected_spans(normalised)
    tokens = sorted(
        (token for token in language_pack.analyze(normalised) if not _overlaps(token, protected)),
        key=lambda token: token.start,
    )
    return IntentDocument(
        lang=lang,
        model=language_pack.model,
        text=normalised,
        tokens=tuple(tokens),
    )


def annotate(
    text: str,
    lang: str = "ru",
    target: str = "acute",
    mode: str = "ambiguous",
    pack: str = "auto",
) -> str:
    """Analyse ``text`` and render it for a TTS engine in one call."""
    return render(analyze(text, lang=lang, pack=pack), target=target, mode=mode)


def _overlaps(token: Token, spans: list[tuple[int, int]]) -> bool:
    return any(token.start < end and start < token.end for start, end in spans)
