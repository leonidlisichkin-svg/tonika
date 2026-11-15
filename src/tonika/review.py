"""A checklist of the words worth a second look before voice-over."""

from __future__ import annotations

from tonika.document import IntentDocument, Reading, Token
from tonika.render import mark_stress


def review(document: IntentDocument, context: int = 30) -> str:
    """List every ambiguous word with the reading Tonika chose and the other readings.

    The result is Markdown, one line per word, with a little text around it. Stress is shown
    with "+" before the stressed vowel.
    """
    lines: list[str] = []
    for token in document.tokens:
        if not token.is_ambiguous:
            continue
        before = document.text[max(0, token.start - context) : token.start]
        after = document.text[token.end : token.end + context]
        snippet = " ".join(f"{before}**{_show(token, token.reading)}**{after}".split())
        others = ", ".join(_show(token, reading) for reading in token.alternatives)
        lines.append(f"- …{snippet}… (or: {others})")
    if not lines:
        return "No ambiguous words.\n"
    return f"Words to check: {len(lines)}\n\n" + "\n".join(lines) + "\n"


def _show(token: Token, reading: Reading) -> str:
    surface = reading.respell if reading.respell is not None else token.form
    return mark_stress(surface, reading.stress, "plus")
