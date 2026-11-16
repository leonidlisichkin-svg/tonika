"""Language pack backed by stressonnx (https://pypi.org/project/stressonnx/, Apache-2.0).

stressonnx runs open accentuation models on onnxruntime: RUAccent for Russian, which reads the
sentence to resolve homographs and restore ё, and silero or vocabulary models for some 25 more
languages. Tonika treats it as a black box with one public contract: ``make_stressor(lang=...)``
returns a callable that maps text to the same text with a combining acute after each stressed
vowel and with ё restored.

For Russian the pack also reads the backend's homograph dictionaries, when they are present, to
tell which words are ambiguous and what their other readings are. Those attributes are private
to stressonnx. Without them the pack still works and reports no alternatives.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator, Mapping
from importlib import metadata
from typing import Any

from tonika.document import Reading, Token
from tonika.packs.base import PackError, Tier
from tonika.segment import iter_chunks
from tonika.text import (
    VOWELS,
    count_vowels,
    fold,
    iter_words,
    locate_marks,
    lower,
    match_case,
    split_marks,
)

Backend = Callable[[str], str]

# In these languages a stress mark on a word's only vowel carries no information.
_SINGLE_VOWEL_LANGS = frozenset({"ru", "uk", "be"})

# In these languages ё is always stressed.
_YO_LANGS = frozenset({"ru", "be"})

# The models that resolve homographs from context, per language: they make a pack tier A.
# The others (silero, simple) give dictionary stress and know no ambiguity: tier B.
_CONTEXT_MODELS: dict[str, frozenset[str]] = {"ru": frozenset({"ruaccent"})}

# stressonnx's default model per language, for when its registry cannot be read.
_KNOWN_DEFAULTS: dict[str, str] = {"ru": "ruaccent"}


class StressonnxPack:
    """Stress and ё for one language, decided by a stressonnx model.

    ``model`` picks a stressonnx model id; ``None`` uses its default for the language.
    ``lowercase`` feeds the model lowercased text, which lets stressonnx 0.0.2 recognise a
    homograph that starts a sentence; it defaults to on for Russian. ``backend`` replaces the
    real model with any callable of the same contract, for tests.
    """

    def __init__(
        self,
        lang: str,
        model: str | None = None,
        *,
        lowercase: bool | None = None,
        backend: Backend | None = None,
        max_chars: int = 600,
    ) -> None:
        self._lang = lang
        self._model_id = model
        if lowercase is None:
            # The environment variable exists for experiments on the golden set.
            setting = os.environ.get("TONIKA_STRESSONNX_LOWERCASE")
            lowercase = lang == "ru" if setting is None else setting == "1"
        self._lowercase = lowercase
        self._backend = backend
        self._model = f"stressonnx:{model or 'custom'}" if backend is not None else None
        self._max_chars = max_chars
        self._load_lock = threading.Lock()
        self._peeked = False
        self._homographs: Mapping[str, object] | None = None
        self._yo_homographs: Mapping[str, object] | None = None

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def model(self) -> str:
        """The model string, built from package metadata: reading it never loads a model."""
        if self._model is None:
            self._model = self._describe()
        return self._model

    @property
    def tier(self) -> Tier:
        model_id = self._model_id or _default_model(self._lang)
        return "A" if model_id in _CONTEXT_MODELS.get(self._lang, frozenset()) else "B"

    @property
    def demo(self) -> bool:
        return False

    def analyze(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        for start, end in iter_chunks(text, self._max_chars):
            chunk = text[start:end]
            if not any(ch.isalpha() for ch in chunk):
                continue
            marked = self._run(chunk)
            stress, yo = locate_marks(chunk, marked)
            tokens.extend(self._tokens(chunk, start, set(stress), set(yo)))
        return tokens

    # ------------------------------------------------------------------

    def _describe(self) -> str:
        """Name the backend version, model id and model revision without creating a stressor."""
        stressonnx = _import_stressonnx()
        model_id = self._model_id or stressonnx.DEFAULT_MODEL.get(self._lang, "default")
        revision = str(getattr(stressonnx.registry, "HF_REPO_REVISION", ""))[:8]
        return f"stressonnx-{metadata.version('stressonnx')}:{model_id}" + (
            f"@{revision}" if revision else ""
        )

    def _load(self) -> Backend:
        # Requests may arrive on several threads at once; the model is loaded only once.
        with self._load_lock:
            if self._backend is not None:
                return self._backend
            stressonnx = _import_stressonnx()
            try:
                backend: Backend = stressonnx.make_stressor(model=self._model_id, lang=self._lang)
            except ValueError as exc:
                raise PackError(str(exc)) from exc
            if self._model is None:
                self._model = self._describe()
            self._backend = backend
            return backend

    def _run(self, chunk: str) -> str:
        backend = self._backend if self._backend is not None else self._load()
        try:
            marked = backend(lower(chunk) if self._lowercase else chunk)
        except Exception as exc:
            raise PackError(f"the {self._lang!r} model failed: {exc}") from exc
        if not self._peeked:
            self._peek(backend)
        return marked

    def _peek(self, backend: Backend) -> None:
        self._peeked = True
        if self._lang != "ru":
            return
        homographs = getattr(backend, "_omographs", None)
        if isinstance(homographs, Mapping):
            self._homographs = homographs
        yo_homographs = getattr(backend, "_yo_homographs", None)
        if isinstance(yo_homographs, Mapping):
            self._yo_homographs = yo_homographs

    def _tokens(self, chunk: str, offset: int, stress: set[int], yo: set[int]) -> Iterator[Token]:
        for start, end, word in iter_words(chunk):
            marks = tuple(i - start for i in range(start, end) if i in stress)
            restored = [i - start for i in range(start, end) if i in yo]
            surface = word
            if restored:
                chars = list(word)
                for i in restored:
                    chars[i] = "Ё" if chars[i] == "Е" else "ё"
                surface = "".join(chars)
            if not marks and self._lang in _YO_LANGS and lower(surface).count("ё") == 1:
                # The models often leave a word with ё unmarked: ё itself says where the stress is.
                marks = (lower(surface).index("ё"),)
            if self._lang in _SINGLE_VOWEL_LANGS and count_vowels(surface) <= 1:
                marks = ()
            reading = Reading(stress=marks, respell=surface if restored else None)
            alternatives = self._alternatives(word, reading)
            if not marks and not restored and not alternatives:
                continue
            yield Token(
                start=offset + start,
                end=offset + end,
                form=word,
                reading=reading,
                kind="yo" if restored else "stress",
                alternatives=alternatives,
                source="model",
            )

    def _alternatives(self, word: str, chosen: Reading) -> tuple[Reading, ...]:
        """The other readings of ``word``, from the backend's homograph dictionaries."""
        if self._homographs is None and self._yo_homographs is None:
            return ()
        plain = lower(word)
        key = lower(chosen.respell) if chosen.respell is not None else plain
        readings: list[Reading] = []

        def add(letters: str, stress: tuple[int, ...]) -> None:
            if count_vowels(letters) <= 1:
                stress = ()
            respell = None if letters == plain else match_case(word, letters)
            reading = Reading(stress=stress, respell=respell)
            if reading != chosen and reading not in readings:
                readings.append(reading)

        if self._homographs is not None:
            variants = self._homographs.get(key) or self._homographs.get(plain) or ()
            if isinstance(variants, list | tuple):
                for variant in variants:
                    if not isinstance(variant, str):
                        continue
                    letters, variant_stress = split_marks(lower(variant))
                    if (
                        variant_stress
                        and len(letters) == len(word)
                        and fold(letters) == fold(word)
                        and all(letters[i] in VOWELS for i in variant_stress)
                    ):
                        add(letters, variant_stress)

        if self._yo_homographs is not None and "е" in plain:
            yo_form = self._yo_homographs.get(plain)
            if isinstance(yo_form, str):
                yo_form = lower(yo_form)
                if len(yo_form) == len(word) and fold(yo_form) == fold(word) and yo_form != plain:
                    if key == yo_form:
                        add(plain, ())
                    else:
                        changed = [
                            i
                            for i, (old, new) in enumerate(zip(plain, yo_form, strict=True))
                            if old != new
                        ]
                        add(yo_form, tuple(changed[:1]))
        return tuple(readings)


def _import_stressonnx() -> Any:
    try:
        import stressonnx
    except ImportError as exc:
        raise PackError(
            "the stressonnx package is not installed; run: pip install 'tonika[ru]'"
        ) from exc
    return stressonnx


def _default_model(lang: str) -> str | None:
    """stressonnx's default model id for ``lang``, read from its registry without loading."""
    try:
        from stressonnx.registry import DEFAULT_MODEL
    except ImportError:
        return _KNOWN_DEFAULTS.get(lang)
    value = DEFAULT_MODEL.get(lang)
    return str(value) if value is not None else _KNOWN_DEFAULTS.get(lang)
