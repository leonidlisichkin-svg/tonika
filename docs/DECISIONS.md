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

## D-009 · 2026-11-16 · stressonnx is used as a black box
The Russian pack calls stressonnx as text in, marked text out, and finds each mark's exact
position in the original text itself (`text.locate_marks`). Nothing else of its API is relied on.
The other readings of a homograph are read from two private tables of the backend; if a future
release drops them, tokens simply lose their alternatives and a test with real models says so.
The dependency is pinned (`stressonnx==0.0.2`) and optional (extra `ru`).

## D-010 · 2026-11-16 · `confidence` is optional
The backend reports no probability. We do not invent one: `confidence` is omitted unless a pack
really measures it. The schema requires every other token field.

## D-011 · 2026-11-16 · The user dictionary is plain text, not YAML
One entry per line (`+Окленд`, `Верещ+агин*`, `JW Marriott = Джей-Д+абл-ю М+арриотт`). It can be
typed anywhere, needs no parser dependency, and uses the notation authors already know.
Format: `docs/DICTIONARY.md`. Supersedes the YAML wording of the first roadmap.

## D-012 · 2026-11-16 · Author marks are converted, not copied
Supersedes the fourth point of D-007. Marks typed by the author are removed before analysis, so
the model sees clean text, and come back as tokens with `source: input`. They are rendered in the
target notation and marked in every mode. The same holds for dictionary readings (`source: user`).
Priority: author marks, then the user dictionary, then the language pack.

## D-013 · 2026-11-16 · Engine presets are TOML inside the package
`src/tonika/engines/*.toml`, read with the standard library, shipped with the wheel, selectable
as `--target <engine id>`. The top-level `engines/` folder of YAML files is gone, and with it the
PyYAML development dependency.

## D-014 · 2026-11-16 · Russian text is lower-cased before the model
The model misses homographs at the start of a sentence when they are capitalised. Measured in CI
on the golden set: 92.3% with lower-casing, 90.2% without. Case is restored from the original
text, so the output is unaffected. `TONIKA_STRESSONNX_LOWERCASE=0` switches it off for experiments.

## D-015 · 2026-11-16 · Stay on stressonnx 0.0.2
The pre-release 0.0.3a41 (default model `ruaccent-silero`) scored 92.0% on the golden set against
92.3% for 0.0.2. No gain, so no pre-release dependency. Repeat the comparison when 0.0.3 is
released, and re-check the model licences then: its registry describes RUAccent as MIT, while
the model card and stressonnx 0.0.2 say Apache-2.0. Both are permissive.

## D-016 · 2026-11-16 · Golden set v1 and the accuracy floor
`data/golden/ru.txt` holds 377 targets in sentences written for this project (CC0), covering
homographs and ё. It contains only hard words, so its accuracy is far below all-word accuracy.
It is not taken from real scripts; that set comes from the script trial (roadmap 1.1).
The floor in `data/golden/baseline.json` is 0.90. It may be raised, never lowered without a new
entry here. Nobody tunes code to the golden sentences.

## D-017 · 2026-11-16 · A lone ё carries the stress
The model often restores ё without a stress mark. In Russian and Belarusian ё is always
stressed, so a word with exactly one ё and no mark is stressed on it. Words with two ё are left
as the model returned them.

## D-018 · 2026-11-16 · Development happens in GitHub Codespaces
Leo works from a work computer with nothing installed, so the project lives in a Codespace:
VS Code in the browser, with Python, uv, Node and Claude Code set up by `.devcontainer/`.
Real models run there, unlike in the Claude Code cloud sandbox. The free allowance of a personal
GitHub account is 120 core-hours a month: 60 hours on the default 2-core machine. Supersedes
"he works from a phone" in the first `CLAUDE.md`.
