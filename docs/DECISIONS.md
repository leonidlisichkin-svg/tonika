# Decisions

Newest last. Each entry: date, decision, reason. Change the plan only through a new entry.

## D-001 · 2026-11-16 · Solve pronunciation intent, not only stress
Stress is the first case. The Intent Document already carries `respell`, `ipa` and `reading_id`,
so heteronyms, polyphones and diacritics fit without a format change.

## D-002 · 2026-11-16 · Three data layers: lexicon, examples, models
A table can store "за́мок / замо́к" but not the rule for choosing. The choice lives in examples
in context; models learn from them.

## D-003 · 2026-11-16 · Wrap open models; do not write them from scratch
Russian will use stressonnx (Apache-2.0, ONNX, RUAccent inside; 0.0.x, so it sits behind our
interface and stays replaceable). Effort goes into what nobody has: the open dataset, renderers,
engine presets and the editor.

## D-004 · 2026-11-16 · Local-first
The library runs in the user's process. A hosted API is a convenience, not a requirement.

## D-005 · 2026-11-16 · Licences
Code Apache-2.0; examples and engine presets CC0-1.0; Wiktionary-derived lexicon under its own
terms in its own folder. Nothing non-commercial. Example: Silero Stress is MIT, but Silero TTS
models are CC BY-NC 4.0, so we describe Silero's notation and ship nothing from it.

## D-006 · 2026-11-16 · Coverage tiers instead of "all languages"
A: context-aware. B: dictionary stress. C: user dictionary only. Published per language.

## D-007 · 2026-11-16 · Phase 0 implementation choices
- Renderers live in one module, `render.py`, not a package: four small functions.
- `--target yo` and `--mode yo` both mean "respelling only". Kept for clarity on the command line.
- Respelling (все → всё) is applied in every mode: it is a spelling fix, never a guess at notation.
- Author-marked words are copied exactly as typed, even if the target notation differs. Converting
  them (e.g. acute → plus) needs offset mapping around inserted marks; deferred to Phase 1.
- With no real pack installed, `pack="auto"` falls back to the demo pack and warns, so the proof
  command runs in CI. The warning goes to stderr; stdout stays clean for piping into TTS.
- Engine targets (`--target yandex-speechkit`) are deferred to Phase 1; Phase 0 targets are notations.

## D-008 · 2026-11-16 · Name
"Tonika" (тоника: the stressed syllable). Free on PyPI and npm on 2026-11-16; nothing published yet.
