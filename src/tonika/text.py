"""Text helpers shared by the pipeline and language packs."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass

COMBINING_ACUTE = "́"
PLUS = "+"

_CYRILLIC_VOWELS = "аеёиоуыэюяіїєәөүұӑӗӳӥӧўӣӯӱ"
_OTHER_VOWELS = "aeiouyáéíóúàèìòùâêîôûäëïöüåæøœãõāēīōūəıաեէըիուօაეიოუ"
VOWELS: frozenset[str] = frozenset(_CYRILLIC_VOWELS + _OTHER_VOWELS)

# A "+" is a stress mark only when it stands right before a Cyrillic vowel ("зам+ок", "+атлас").
# Elsewhere ("2+2", "A+B", "плюс+минус") it is ordinary text.
_PLUS_VOWELS = _CYRILLIC_VOWELS + _CYRILLIC_VOWELS.upper()

# A word is a run of letters. Combining marks stay attached to their letter, and a stress "+"
# stays inside the word it marks. Hyphens and apostrophes separate words.
WORD_RE = re.compile(rf"(?:(?:\+(?=[{_PLUS_VOWELS}]))?[^\W\d_][̀-ͯ]*)+")


def normalize(text: str) -> str:
    """Return the NFC form that all Tonika offsets refer to."""
    return unicodedata.normalize("NFC", text)


def iter_words(text: str) -> Iterator[tuple[int, int, str]]:
    """Yield ``(start, end, word)`` for every word in ``text``."""
    for match in WORD_RE.finditer(text):
        yield match.start(), match.end(), match.group()


def lower(text: str) -> str:
    """Lowercase without changing the length, so offsets stay valid.

    ``str.lower()`` turns the Turkic capital İ into two code points; this keeps the first.
    """
    return "".join(low if len(low := ch.lower()) == 1 else low[0] for ch in text)


def fold(text: str) -> str:
    """Lowercase and treat ё as е: the form used to compare a word across spellings."""
    return lower(text).replace("ё", "е")


def count_vowels(word: str) -> int:
    return sum(1 for ch in lower(word) if ch in VOWELS)


def split_marks(word: str) -> tuple[str, tuple[int, ...]]:
    """Separate a word from the stress marks typed in it.

    Returns the word without marks and the zero-based indices of its stressed letters, in the
    order they were typed. Understands "+" before a letter and a combining acute after a vowel:
    ``"зам+ок"`` and ``"замо́к"`` both give ``("замок", (3,))``.
    """
    letters: list[str] = []
    stress: list[int] = []
    pending = False
    for ch in word:
        if ch == PLUS:
            pending = True
            continue
        if ch == COMBINING_ACUTE and letters and lower(letters[-1]) in VOWELS:
            if len(letters) - 1 not in stress:
                stress.append(len(letters) - 1)
            continue
        if pending:
            if len(letters) not in stress:
                stress.append(len(letters))
            pending = False
        letters.append(ch)
    return "".join(letters), tuple(stress)


def is_author_marked(word: str) -> bool:
    """True when the author already marked stress in this word."""
    return bool(split_marks(word)[1])


@dataclass(frozen=True, slots=True)
class AuthorWord:
    """A word the author marked, located in the clean text."""

    start: int
    end: int
    stress: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CleanText:
    """Text with the author's stress marks removed, and the way back to the original.

    ``lo[i]`` and ``hi[i]`` bound clean character ``i`` in the original text, including a "+"
    typed before it or an acute typed after it.
    """

    text: str
    lo: tuple[int, ...]
    hi: tuple[int, ...]
    author_words: tuple[AuthorWord, ...]

    def span(self, start: int, end: int) -> tuple[int, int]:
        """Map a non-empty clean span to the original text."""
        return self.lo[start], self.hi[end - 1]


def strip_author_marks(text: str) -> CleanText:
    """Remove the author's stress marks so language packs see ordinary text."""
    chars: list[str] = []
    lo: list[int] = []
    hi: list[int] = []
    words: list[AuthorWord] = []

    def copy(start: int, end: int) -> None:
        for i in range(start, end):
            chars.append(text[i])
            lo.append(i)
            hi.append(i + 1)

    position = 0
    for match in WORD_RE.finditer(text):
        copy(position, match.start())
        position = match.end()
        _, stress = split_marks(match.group())
        if not stress:
            copy(match.start(), match.end())
            continue
        word_start = len(chars)
        pending: int | None = None
        for i in range(match.start(), match.end()):
            ch = text[i]
            if ch == PLUS:
                pending = i
                continue
            if ch == COMBINING_ACUTE and len(chars) > word_start and lower(chars[-1]) in VOWELS:
                hi[-1] = i + 1
                continue
            chars.append(ch)
            lo.append(i if pending is None else pending)
            hi.append(i + 1)
            pending = None
        words.append(AuthorWord(word_start, len(chars), stress))
    copy(position, len(text))
    return CleanText("".join(chars), tuple(lo), tuple(hi), tuple(words))


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


def locate_marks(source: str, marked: str) -> tuple[list[int], list[int]]:
    """Find where a marked rendering of ``source`` puts stress and restores ё.

    ``marked`` is what an accentuator returned for ``source``: the same letters with a combining
    acute after each stressed one and some е turned into ё. It may have dropped characters or
    changed letter case; it must not reorder letters. Returns the offsets in ``source`` of the
    stressed letters and of the е that became ё. A mark that cannot be traced back is dropped
    rather than guessed.
    """
    base: list[str] = []
    marked_at: list[int] = []
    for ch in marked:
        if ch == COMBINING_ACUTE:
            if base:
                marked_at.append(len(base) - 1)
        else:
            base.append(ch)
    mapping = _embed("".join(base), source)
    stress = sorted({j for i in marked_at if (j := mapping[i]) is not None})
    yo = [
        j
        for i, ch in enumerate(base)
        if ch in "ёЁ" and (j := mapping[i]) is not None and source[j] in "еЕ"
    ]
    return stress, yo


def _embed(base: str, source: str) -> list[int | None]:
    """Map each character of ``base`` to its position in ``source``."""
    folded_base, folded_source = fold(base), fold(source)
    if folded_base == folded_source:
        return list(range(len(base)))
    # The usual difference is dropped characters, which makes base a subsequence of source.
    mapping: list[int | None] = []
    j = 0
    for ch in folded_base:
        j = folded_source.find(ch, j)
        if j < 0:
            break
        mapping.append(j)
        j += 1
    else:
        return mapping
    # Something was inserted or rewritten: align what can be aligned.
    import difflib

    mapping = [None] * len(base)
    matcher = difflib.SequenceMatcher(None, folded_base, folded_source, autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            mapping[block.a + k] = block.b + k
    return mapping
