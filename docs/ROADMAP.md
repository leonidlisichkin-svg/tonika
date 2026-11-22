# Roadmap

Each phase has one exit criterion. The next phase starts only when the current one is closed.
Each unchecked item is one pull request. An item with a number has a ready brief in
[`docs/briefs/`](briefs/); specs it relies on are in [`docs/specs/`](specs/).

## Phase 0 — Foundation

- [x] Repository, `CLAUDE.md`, plan documents in `docs/`
- [x] Intent Document v1: schema, dataclasses, validation, JSON round-trip
- [x] `LanguagePack` interface, registry, deterministic demo pack
- [x] Renderers `acute`, `plus`, `upper`, `yo`; modes `ambiguous`, `all`, `yo`
- [x] CLI `tonika annotate` (argument, file, stdin; text or JSON output)
- [x] Engine presets: Yandex SpeechKit, Silero, generic acute, generic upper
- [x] CI: lint, type check, offline tests, proof command; `models` job
- [x] Licence audit of planned components (`LICENSES.md`)

**Exit:** green CI. **Closed** on 2026-11-17 (D-020).

## Phase 1 — Russian core and CLI

- [x] Russian pack backed by stressonnx behind `LanguagePack`; the backend is swappable
- [x] Results mapped back to the exact input offsets; author marks kept and converted
- [x] User dictionary: a plain-text file of forced readings, highest priority after author marks
- [x] Engine presets selectable as targets (`--target yandex-speechkit`)
- [x] Golden set `data/golden/ru.txt`: 377 homograph and ё targets in original sentences
- [x] Evaluation harness: accuracy and speed, posted as a pull request comment, with a floor
- [x] Long input: sentence chunks, constant memory
- [x] Checklist of ambiguous words for a human (`--review`)
- [x] **1.1** Long-text trial: a 30-minute public-domain text through `tonika trial` in CI;
      the text is preserved, and speed, memory and review load are recorded
- [x] **1.2** Compare the stressonnx Russian models on the golden set; choose the default
      (`docs/ACCURACY.md`, D-022); line endings kept; cross-machine drift traced and bounded (D-021)

**Exit:** a 30-minute text passes through the CLI changed only by marks, and its numbers are
recorded in `docs/TRIALS.md`. **Closed** on 2026-11-17.

Measured on 2026-11-16: 92.3% (348 of 377) on the golden set, which holds only hard words.

## Phase 2 — Web editor and API

Specs: `docs/specs/api-v1.md`, `docs/specs/web-editor.md`.

- [x] **2.1** HTTP API as the optional extra `api`: `tonika serve`, `POST /v1/annotate`,
      `GET /v1/engines`, `GET /v1/languages`; no text stored
- [ ] **2.2** Browser core: `render` in TypeScript proven identical to Python by shared test
      vectors; block splitting; API client
- [ ] **2.3** Editor screen: paste, progressive result, engine and mode, copy
- [ ] **2.4** Review flow: doubtful words, choosing a reading, personal dictionary
- [ ] **2.5** One Docker image; hosting chosen with Leo at the start of the item

**Exit:** a 30-minute text prepared from a phone using only the web editor.

## Phase 3 — Open dataset

Specs: `docs/specs/dataset-loop.md`, `docs/specs/decision-lists.md`.

- [ ] **3.1** Example records: checks, `tonika data check`, a CI step over `data/examples/`
- [ ] **3.2** Seed examples: 300 or more original sentences for frequent Russian homographs
- [ ] **3.3** Decision lists: trainer and pack, deterministic, learnt from the examples
- [ ] **3.4** Corrections layer: learnt rules override the Russian model where they are sure
- [ ] Collection endpoint and review queue (storage chosen with Leo)
- [ ] Daily bot pull request with accepted examples; first numbered data release

**Exit:** a correction made in the editor changes the engine's answer within a day, visible in git history.

## Phase 4 — Distribution

Spec for the whole phase: `docs/specs/distribution.md`.

- [ ] PyPI package with trusted publishing (the PyPI account is Leo's)
- [ ] MCP server: one tool, `annotate`
- [ ] LiveKit and Pipecat text transforms; presets for ElevenLabs and OpenAI
- [ ] npm client for the HTTP API
- [ ] Documentation site and public accuracy table

**Exit:** three external projects use the library.

## Phase 5 — Languages (ongoing)

- [ ] Ukrainian and Belarusian: tier B → A
- [ ] English heteronyms on open sets
- [ ] Hebrew (Phonikud) and Mandarin (g2pW) wrappers

**Exit per language:** golden set, published accuracy, named language editor.

## Phase 6 — Scale and sustainability

- [ ] Hosted API with keys, quotas and guarantees; team dictionaries
- [ ] Grants and sponsors; project governance

**Exit:** the project covers its own costs.
