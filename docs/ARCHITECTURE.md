# Architecture

Tonika first turns text into an **Intent Document**, a list of pronunciation decisions with
offsets into the input, and only then renders it in a notation. Separating analysis from rendering
is the central design decision: one analysis serves every TTS engine.

## Pipeline

```
text ─▶ normalise (NFC) ─▶ language pack ─▶ drop author-marked words ─▶ Intent Document ─▶ renderer ─▶ text for TTS
```

1. **Normalise.** Unicode NFC. All offsets refer to the normalised text.
2. **Language pack.** Finds the words it has an opinion about and decides their reading.
   A pack may use a lexicon, rules, a neural model or a mix.
3. **Author marks.** Words the author already marked (combining acute or `+`) are removed from
   the decisions, so they are copied exactly as typed. (Phase 0 behaviour; converting their
   notation is a later improvement, see DECISIONS.md.)
4. **Intent Document.** Validated on construction: offsets in range, forms match the text,
   tokens sorted and non-overlapping, stress indices inside the word.
5. **Renderer.** Copies text between tokens unchanged and writes each token in the target
   notation. The input layout always survives.

Planned stage, Phase 1: a **user dictionary** of forced readings (names, brands, places) applied
after the pack, with the highest priority.

## Intent Document

Specified in [`spec/intent-document.schema.json`](../spec/intent-document.schema.json) and
implemented in `src/tonika/document.py`.

```json
{
  "spec": "1.0",
  "lang": "ru",
  "model": "fake-0",
  "text": "В старом замке сломался замок.",
  "tokens": [
    {"start": 9, "end": 14, "form": "замке", "kind": "stress",
     "reading": {"stress": [1]}, "alternatives": [{"stress": [4]}],
     "confidence": 0.97, "source": "lexicon"}
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
- A token with `alternatives` is *ambiguous*; the default render mode marks only those.

## Language packs

Interface: `tonika.packs.base.LanguagePack` — properties `lang`, `model`, `demo` and a method
`analyze(text) -> list[Token]`. Three kinds are planned:

| Kind | Example | When |
| --- | --- | --- |
| Wrapper around an external model | Russian via stressonnx (RUAccent inside) | A strong open model exists |
| Universal pack | Lexicon + decision lists learnt from the dataset | Any language with examples |
| Pass-through | User dictionary only | Everything else |

`get_pack(lang, "auto")` picks the best installed pack. In Phase 0 only `FakePack`, a deterministic
demo, exists; "auto" falls back to it with a `DemoPackWarning`.

## Renderers

| Notation | Output | Rule |
| --- | --- | --- |
| `acute` | за́мок | U+0301 after the stressed letter |
| `plus` | з+амок | `+` before the stressed letter |
| `upper` | зАмок | stressed letter upper-cased |
| `yo` | всё | respelling only, no stress marks |

Modes: `ambiguous` (only tokens with alternatives), `all`, `yo` (respelling only). Respelling is
applied in every mode. Planned: `ipa`, `ssml`.

Engine presets in `engines/*.yaml` record which notation each TTS engine honours, who verified it
and when. They are data, edited by the community like the dataset.

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
