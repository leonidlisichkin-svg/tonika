# Architecture

Tonika first turns text into an **Intent Document**, a list of pronunciation decisions with
offsets into the input, and only then renders it in a notation. Separating analysis from rendering
is the central design decision: one analysis serves every TTS engine.

## Pipeline

```
text ─▶ NFC ─▶ strip author marks ─▶ user dictionary ─┐
                       │                              ├─▶ Intent Document ─▶ renderer ─▶ text for TTS
                       └─▶ language pack (by chunks) ─┘
```

1. **Normalise.** Unicode NFC. All offsets refer to the normalised text.
2. **Author marks.** Stress the author typed (combining acute or `+` before a vowel) is taken out
   of the text and remembered. The model sees clean text; the marks return as tokens with
   `source: input`.
3. **User dictionary.** Forced readings for names, places and brands (`docs/DICTIONARY.md`),
   tokens with `source: user`.
4. **Language pack.** Reads the clean text in sentence chunks (`segment.iter_chunks`, constant
   memory for long scripts) and decides the reading of every word it knows. A pack may use a
   lexicon, rules, a neural model or a mix.
5. **Merge.** Priority: author marks, then the dictionary, then the pack. Tokens are mapped back
   to offsets in the text as typed.
6. **Intent Document.** Validated on construction: offsets in range, forms match the text,
   tokens sorted and non-overlapping, stress indices inside the word.
7. **Renderer.** Copies text between tokens unchanged and writes each token in the target
   notation. The input layout always survives.

## Intent Document

Specified in [`spec/intent-document.schema.json`](../spec/intent-document.schema.json) and
implemented in `src/tonika/document.py`.

```json
{
  "spec": "1.0",
  "lang": "ru",
  "model": "stressonnx-0.0.2:ruaccent@b8ba7afd",
  "text": "В старом замке сломался замок.",
  "tokens": [
    {"start": 9, "end": 14, "form": "замке", "kind": "stress",
     "reading": {"stress": [1]}, "alternatives": [{"stress": [4]}],
     "source": "model"}
  ]
}
```

- `start`, `end`: code-point offsets into `text`.
- `reading.stress`: zero-based letter indices into the surface form (the `respell` if present,
  else `form`). The first is the primary stress.
- `reading` may also carry `respell` (все → всё), `ipa` and `reading_id` (a lexicon entry). The
  same document therefore covers a Russian homograph, an English heteronym or a Chinese polyphone.
- `kind`: stress, yo, heteronym, polyphone, diacritics, custom.
- `source`: model, lexicon, rules, user, input.
- `confidence` is optional and present only when a pack really measures it.
- A token with `alternatives` is *ambiguous*; the default render mode marks only those.

## Language packs

Interface: `tonika.packs.base.LanguagePack` — properties `lang`, `model`, `tier`, `demo` and a
method `analyze(text) -> list[Token]`.

| Kind | Example | When |
| --- | --- | --- |
| Wrapper around an external model | `StressonnxPack`: Russian via stressonnx (RUAccent inside) | A strong open model exists |
| Universal pack (Phase 3) | Lexicon + decision lists learnt from the dataset | Any language with examples |
| Pass-through | User dictionary only | Everything else |

`get_pack(lang, "auto")` picks the best installed pack and falls back to `FakePack`, a
deterministic demo, with a `DemoPackWarning`. `"stressonnx:<model id>"` selects another model of
the backend.

**Coverage tiers.** A: context-aware, knows which words are ambiguous (Russian). B: dictionary
stress without context (Ukrainian, Belarusian and others through the same backend). C: user
dictionary only. The default render mode is `ambiguous` for tier A and `all` otherwise.

**How the Russian pack works.** The backend is a black box: text in, text with marks out. It may
drop or change characters, so the pack locates every mark in its own input by alignment
(`text.locate_marks`) instead of trusting the backend's output layout. Input is lower-cased for
the model and case is restored from the original. A word with a single ё and no mark is stressed
on the ё. The other readings of a homograph come from the backend's homograph tables. The model
string names everything that determines the result:
`stressonnx-0.0.2:ruaccent@b8ba7afd` is backend version, model id and model revision.

## Evaluation

`tonika eval <file>` runs a pack over sentences whose target words carry the expected stress
(`evaluate.py`), and reports accuracy, unmarked words and speed. CI runs it with real models on
`data/golden/ru.txt`, posts the report on the pull request and fails below the floor in
`data/golden/baseline.json`. The golden set is held out: nothing is trained on it or tuned to it.

## Renderers

| Notation | Output | Rule |
| --- | --- | --- |
| `acute` | за́мок | U+0301 after the stressed letter |
| `plus` | з+амок | `+` before the stressed letter |
| `upper` | зАмок | stressed letter upper-cased |
| `yo` | всё | respelling only, no stress marks |

Modes: `ambiguous` (only tokens with alternatives), `all`, `yo` (respelling only). Respelling is
applied in every mode. Planned: `ipa`, `ssml`.

Tokens with `source: input` or `source: user` are marked in every mode: the author chose them.

Engine presets in `src/tonika/engines/*.toml` record which notation each TTS engine honours, who
verified it and when. A preset id works wherever a notation does (`--target yandex-speechkit`).
They are data, edited by the community like the dataset.

`review.review(document)` lists the ambiguous words with their context and the other readings, a
checklist for the author before voicing.

## Stack

| Layer | Choice |
| --- | --- |
| Core | Python 3.11+, strict typing, no runtime dependencies |
| Models | ONNX Runtime on CPU; no torch at runtime |
| API (Phase 2) | FastAPI in one Docker container |
| Web (Phase 2) | Vite, React, TypeScript; static build served by the same container |
| Quality | pytest, ruff, mypy, GitHub Actions |
| Data | JSONL in git, mirrored to Hugging Face |

## Scale

Local-first: the heavy work runs in the user's process, so usage growth does not grow our costs.
The hosted API is stateless, caches by hash of (text, language, settings, model version), and
scales horizontally. Model and data releases are versioned; clients can pin a version.
