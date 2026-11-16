"""The public entry points: analyse text, then render it."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from tonika.dictionary import UserDictionary
from tonika.document import IntentDocument, Reading, Token
from tonika.engines import resolve_target
from tonika.packs import LanguagePack, get_pack
from tonika.render import MODES, render
from tonika.text import CleanText, normalize, strip_author_marks

DictionaryLike = UserDictionary | str | Path | None


def analyze(
    text: str,
    lang: str = "ru",
    pack: str = "auto",
    dictionary: DictionaryLike = None,
) -> IntentDocument:
    """Return an Intent Document for ``text``.

    The text is NFC-normalised first; all offsets refer to the normalised text. ``dictionary``
    is a :class:`UserDictionary` or the path of a dictionary file.
    """
    return analyze_with(get_pack(lang, pack), text, _dictionary(dictionary))


def analyze_with(
    pack: LanguagePack,
    text: str,
    dictionary: UserDictionary | None = None,
) -> IntentDocument:
    """Analyse ``text`` with a pack instance.

    Three sources decide how a word is read, in this order of priority: stress marks the author
    typed in the text, the user dictionary, the language pack. A higher source silences the lower
    ones for the words it covers.
    """
    original = normalize(text)
    clean = strip_author_marks(original)

    author = [
        Token(
            start=word.start,
            end=word.end,
            form=clean.text[word.start : word.end],
            reading=Reading(stress=word.stress),
            confidence=1.0,
            source="input",
        )
        for word in clean.author_words
    ]
    taken = [(token.start, token.end) for token in author]
    user = [
        token
        for token in (dictionary.find(clean.text) if dictionary is not None else [])
        if not _overlaps(token, taken)
    ]
    taken += [(token.start, token.end) for token in user]
    decided = [token for token in pack.analyze(clean.text) if not _overlaps(token, taken)]

    tokens = sorted([*author, *user, *decided], key=lambda token: token.start)
    if clean.author_words:
        tokens = [_to_original(token, clean, original) for token in tokens]
    return IntentDocument(lang=pack.lang, model=pack.model, text=original, tokens=tuple(tokens))


def annotate(
    text: str,
    lang: str = "ru",
    target: str = "acute",
    mode: str | None = None,
    pack: str = "auto",
    dictionary: DictionaryLike = None,
) -> str:
    """Analyse ``text`` and render it for a TTS engine in one call.

    ``target`` is a notation (``acute``, ``plus``, ``upper``, ``yo``) or an engine id such as
    ``yandex-speechkit``. ``mode`` defaults to what the language pack supports: see
    :func:`default_mode`.
    """
    notation = resolve_target(target)
    if mode is not None and mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; choose from {', '.join(MODES)}")
    language_pack = get_pack(lang, pack)
    document = analyze_with(language_pack, text, _dictionary(dictionary))
    return render(document, notation, mode or default_mode(language_pack))


def default_mode(pack: LanguagePack) -> str:
    """``ambiguous`` for packs that know which words are ambiguous, ``all`` for the rest."""
    return "ambiguous" if pack.tier == "A" else "all"


def _dictionary(value: DictionaryLike) -> UserDictionary | None:
    if value is None or isinstance(value, UserDictionary):
        return value
    return UserDictionary.load(value)


def _overlaps(token: Token, spans: list[tuple[int, int]]) -> bool:
    return any(token.start < end and start < token.end for start, end in spans)


def _to_original(token: Token, clean: CleanText, original: str) -> Token:
    """Move a token from the clean text back to the text the author typed."""
    start, end = clean.span(token.start, token.end)
    form = original[start:end]
    reading = token.reading
    if form != token.form and reading.respell is None:
        # The typed word carries stress marks; the surface is the word without them.
        reading = replace(reading, respell=token.form)
    return replace(token, start=start, end=end, form=form, reading=reading)
