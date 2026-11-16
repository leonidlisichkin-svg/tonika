"""User dictionary: readings the author fixes, whatever the language pack thinks.

A dictionary is a plain text file, one entry per line::

    # names and places
    +Окленд                        stress: put + before the stressed vowel
    Лис+ичкин*                     * also matches longer forms: Лисичкина, Лисичкину
    Корол+ёв                       restores ё when the text has Королев
    Н+овая Зел+андия               phrases work too
    JW Marriott = Джей-Д+абл-ю М+арриотт    replacement: what the engine should read

Matching ignores letter case and treats ё and е as the same letter. A combining acute after the
vowel works wherever + does. Later entries override earlier ones with the same key.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tonika.document import Reading, Token
from tonika.text import WORD_RE, fold, iter_words, lower, match_case, normalize, split_marks

_COMMENT_RE = re.compile(r"(?:^|\s)#.*$")
_ASSIGN_RE = re.compile(r"\s=\s")


class DictionaryError(ValueError):
    """Raised when a dictionary line cannot be understood."""


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """One forced reading.

    ``key`` is the folded text to match. A stress entry keeps ``letters``, the key as typed in
    lower case, so ё can be restored. A replacement entry keeps ``respell`` instead.
    """

    key: str
    stress: tuple[int, ...]
    letters: str | None = None
    respell: str | None = None
    prefix: bool = False


class UserDictionary:
    """A set of forced readings that can be applied to text."""

    def __init__(self, entries: Iterable[DictionaryEntry] = ()) -> None:
        self._words: dict[str, DictionaryEntry] = {}
        self._prefixes: dict[str, DictionaryEntry] = {}
        self._phrases: dict[str, tuple[DictionaryEntry, re.Pattern[str]]] = {}
        for entry in entries:
            self.add(entry)

    def __len__(self) -> int:
        return len(self._words) + len(self._prefixes) + len(self._phrases)

    def add(self, entry: DictionaryEntry) -> None:
        if entry.prefix:
            self._prefixes[entry.key] = entry
        elif _is_single_word(entry.key):
            self._words[entry.key] = entry
        else:
            pattern = re.compile(rf"(?<![^\W_]){re.escape(entry.key)}(?![^\W_])")
            self._phrases[entry.key] = (entry, pattern)

    @classmethod
    def parse(cls, text: str, source: str = "<dictionary>") -> UserDictionary:
        """Read a dictionary from its text form."""
        dictionary = cls()
        for number, raw in enumerate(text.splitlines(), 1):
            line = _COMMENT_RE.sub("", raw).strip()
            if line:
                dictionary.add(_parse_line(line, f"{source}:{number}"))
        return dictionary

    @classmethod
    def load(cls, *paths: str | Path) -> UserDictionary:
        """Read one or more dictionary files; later files override earlier ones."""
        dictionary = cls()
        for path in paths:
            loaded = cls.parse(Path(path).read_text(encoding="utf-8"), source=str(path))
            dictionary._words.update(loaded._words)
            dictionary._prefixes.update(loaded._prefixes)
            dictionary._phrases.update(loaded._phrases)
        return dictionary

    def find(self, text: str) -> list[Token]:
        """Return a token for every place in ``text`` where an entry applies.

        ``text`` must be clean: NFC, without stress marks. Tokens are sorted and do not overlap;
        where entries compete for the same words, the longest match wins.
        """
        if not len(self):
            return []
        folded = fold(text)
        found: list[tuple[int, int, DictionaryEntry]] = []
        for entry, pattern in self._phrases.values():
            found.extend((m.start(), m.end(), entry) for m in pattern.finditer(folded))
        prefixes = sorted(self._prefixes.values(), key=lambda e: len(e.key), reverse=True)
        for start, end, _ in iter_words(text):
            key = folded[start:end]
            match = self._words.get(key)
            if match is None:
                match = next((p for p in prefixes if key.startswith(p.key)), None)
            if match is not None:
                found.append((start, end, match))

        found.sort(key=lambda item: (item[0] - item[1], item[0]))
        taken: list[tuple[int, int, DictionaryEntry]] = []
        for start, end, entry in found:
            if all(end <= s or e <= start for s, e, _ in taken):
                taken.append((start, end, entry))
        taken.sort(key=lambda item: item[0])
        return [_token(text, start, end, entry) for start, end, entry in taken]


def _is_single_word(key: str) -> bool:
    return WORD_RE.fullmatch(key) is not None


def _parse_line(line: str, where: str) -> DictionaryEntry:
    parts = _ASSIGN_RE.split(line, maxsplit=1)
    if len(parts) == 1 and "=" in line:
        parts = [part.strip() for part in line.split("=", 1)]
    if len(parts) == 2:
        key_text, value = normalize(parts[0].strip()), normalize(parts[1].strip())
        if not key_text or not value:
            raise DictionaryError(f"{where}: expected 'text = replacement'")
        if key_text.endswith("*"):
            raise DictionaryError(f"{where}: an entry with * cannot have a replacement")
        respell, stress = split_marks(value)
        if not respell:
            raise DictionaryError(f"{where}: the replacement is empty")
        return DictionaryEntry(key=fold(key_text), stress=stress, respell=respell)

    prefix = line.endswith("*")
    body = normalize(line[:-1].rstrip() if prefix else line)
    letters, stress = split_marks(body)
    if not any(ch.isalpha() for ch in letters):
        raise DictionaryError(f"{where}: no word in {line!r}")
    if not stress:
        raise DictionaryError(
            f"{where}: no stress mark in {line!r}; put + before the stressed vowel, like зам+ок"
        )
    if prefix and not _is_single_word(letters):
        raise DictionaryError(f"{where}: an entry with * must be a single word")
    return DictionaryEntry(key=fold(letters), stress=stress, letters=lower(letters), prefix=prefix)


def _token(text: str, start: int, end: int, entry: DictionaryEntry) -> Token:
    form = text[start:end]
    if entry.respell is not None:
        reading = Reading(stress=entry.stress, respell=entry.respell)
    else:
        letters = entry.letters or ""
        head = form[: len(letters)]
        respell = None
        if lower(head) != letters:
            respell = match_case(head, letters) + form[len(letters) :]
        reading = Reading(stress=entry.stress, respell=respell)
    return Token(
        start=start,
        end=end,
        form=form,
        reading=reading,
        kind="custom",
        confidence=1.0,
        source="user",
    )
