"""Text helpers shared by the pipeline and language packs."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

COMBINING_ACUTE = "́"

# A word is a run of letters. Combining marks stay attached to their letter, and a "+" written
# before a letter (the author's own stress mark, e.g. "з+амок" or "+атлас") stays inside the word.
WORD_RE = re.compile(r"(?:\+?[^\W\d_][̀-ͯ]*)+")


def normalize(text: str) -> str:
    """Return the NFC form that all Tonika offsets refer to."""
    return unicodedata.normalize("NFC", text)


def iter_words(text: str) -> Iterator[tuple[int, int, str]]:
    """Yield ``(start, end, word)`` for every word in ``text``."""
    for match in WORD_RE.finditer(text):
        yield match.start(), match.end(), match.group()


def is_author_marked(word: str) -> bool:
    """True when the author already marked stress in this word with an acute or a plus."""
    return COMBINING_ACUTE in word or "+" in word


def protected_spans(text: str) -> list[tuple[int, int]]:
    """Spans of words the author marked themselves. Tonika must leave them untouched."""
    return [(start, end) for start, end, word in iter_words(text) if is_author_marked(word)]


def match_case(template: str, word: str) -> str:
    """Give ``word`` the letter case of ``template``: "Все" + "всё" gives "Всё"."""
    if len(template) == len(word):
        return "".join(
            new.upper() if old.isupper() else new.lower()
            for old, new in zip(template, word, strict=True)
        )
    if template.isupper() and len(template) > 1:
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word
