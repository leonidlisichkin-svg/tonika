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

## D-019 · 2026-11-17 · Two roles: the conductor and the Codespace
Strategy and briefs are made in a Claude chat with Leo (the conductor), which sees the plan but
not the machine. Code is written by Claude Code in the Codespace, one brief per pull request.
The repository is the only source of truth: a brief from the conductor is saved under
`docs/briefs/` before it is built, and the three closing lines of each session are what Leo
carries back. The first Codespace was opened and signed in on this date; what was learnt is in
`docs/CODESPACES.md`.

## D-020 · 2026-11-17 · Engine-neutral: no engine, product or single user gates a phase
Leo's decision. Tonika serves any TTS engine, so the plan no longer waits on one.
- The Fliki listening test (roadmap 0.1) and the voiced script trial (old 1.1) are withdrawn.
  Phase 0 closes on green CI. Item 1.1 becomes the long-text trial: a 30-minute public-domain
  text runs through `tonika trial` in CI, which proves the text is changed only by
  pronunciation marks and records speed, memory and review load in `docs/TRIALS.md`.
- Every phase exit must be checkable by CI or by anyone with the repository.
- Engine presets are verified by whoever uses that engine, who says so in `verified_by`.
- The golden set from real text promised in D-016 now comes from the Phase 3 examples; there is
  no `ru-scripts.txt`.

## D-021 · 2026-11-17 · Determinism: exact for Tonika, bounded for a neural backend
The conductor's decision, adjusted to the evidence in `docs/TRIALS.md`. On the trial text, a CI
runner with an Intel Xeon 6975P-C (x86-64-v4: AVX-512 and AMX) gave no stress to two words,
«победах» and «тайне», that the Codespace (AMD EPYC 7763, x86-64-v3) and other runners stress
correctly: 3,181 words given stress against 3,183, a drift of 0.063%. On one machine the output
never changed, across runs and thread counts, and a CI runner with the Codespace's processor
gave the same digest. onnxruntime picks its arithmetic kernels by
processor, which tips close decisions. stressonnx 0.0.2 builds its sessions with no options and
reads no settings, so nothing can be pinned without patching it, which we do not do.
- Principle 4 now reads: Tonika's own code gives bit-identical output on any machine. A neural
  backend gives identical output on the same machine and may differ across processors in close
  decisions; CI records the processor and the output digest, and such drift must stay under 0.1%
  of words given stress on the trial text.
- CI enforces it: `tonika trial --reference data/trials/reference.json` fails when words given
  stress differ from the reference for the same model by more than 0.1%. The measure is a net
  count; the digest shows whether any decision differs at all. The reference is the Codespace
  run, and it is replaced only together with the model string.
- The trial's Intent Document is kept as a CI artifact for 30 days, so any drift can be traced
  to its words.

## D-022 · 2026-11-17 · `ruaccent` stays the default Russian model
Measured in `docs/ACCURACY.md` for every stressonnx 0.0.2 model that serves Russian: `ruaccent`
92.3% on the golden set, `simple` 23.1%, `silero` 9.8%. The rule (highest accuracy; within one
point, fewer words to review, then faster and smaller) picks `ruaccent` with no tie to break.
No stable stressonnx 0.0.3 exists, so D-015 stands. The floor stays at 0.90.
