"""Cut long text into sentence-sized chunks for language models."""

from __future__ import annotations

import re
from collections.abc import Iterator

# The end of a sentence: closing punctuation, optional closing quotes or brackets, then space.
# A line break always ends a chunk.
_BOUNDARY = re.compile(r"[.!?…]+[\"'»”’)\]]*[^\S\n]+|\n+")

# What may stand between the end of a quoted sentence and the words that attribute it.
_LEAD_IN = re.compile(r"[—–\-\s]*")

_SOFT_BREAKS = ("; ", ": ", ", ", " — ", " – ", " ")


def iter_chunks(text: str, max_chars: int = 600) -> Iterator[tuple[int, int]]:
    """Yield ``(start, end)`` spans that cover ``text`` exactly, one sentence at a time.

    Models read a limited number of tokens and decide better with a whole sentence in view, so
    chunks end at sentence boundaries. A sentence longer than ``max_chars`` is cut at the
    nearest punctuation or space. A chunk does not end where the text goes on in lower case:
    after an abbreviation ("т. е. так") or before the attribution of a quote («Кто?» — спросил он).
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    start = 0
    for match in _BOUNDARY.finditer(text):
        end = match.end()
        if "\n" not in match.group():
            following = _LEAD_IN.match(text, end).end()  # type: ignore[union-attr]
            if following < len(text) and text[following].islower():
                continue
        yield from _split_long(text, start, end, max_chars)
        start = end
    if start < len(text):
        yield from _split_long(text, start, len(text), max_chars)


def _split_long(text: str, start: int, end: int, max_chars: int) -> Iterator[tuple[int, int]]:
    while end - start > max_chars:
        window = text[start : start + max_chars]
        cut = max_chars
        for separator in _SOFT_BREAKS:
            index = window.rfind(separator)
            if index >= max_chars // 3:
                cut = index + len(separator)
                break
        yield start, start + cut
        start += cut
    if end > start:
        yield start, end
