# Roadmap

Each phase has one exit criterion. The next phase starts only when the current one is closed.
Durations are guides for one person working evenings.

## Phase 0 — Foundation

- [x] Repository, `CLAUDE.md`, plan documents in `docs/`
- [x] Intent Document v1: schema, dataclasses, validation, JSON round-trip
- [x] `LanguagePack` interface, registry, deterministic demo pack
- [x] Renderers `acute`, `plus`, `upper`, `yo`; modes `ambiguous`, `all`, `yo`
- [x] CLI `tonika annotate` (argument, file, stdin; text or JSON output)
- [x] Engine presets: Yandex SpeechKit, Silero, generic acute, generic upper
- [x] CI: lint, type check, offline tests, proof command; reserved `models` job
- [x] Licence audit of planned components (`LICENSES.md`)
- [ ] Fliki listening test: which notation does the channel's voice honour? (Leo)

**Exit:** green CI, and the notation the Fliki voice honours is recorded in `DECISIONS.md`.

## Phase 1 — Russian core and CLI (1–2 weeks)

- [ ] Russian pack backed by stressonnx, behind `LanguagePack`; keep a direct RUAccent backend possible
- [ ] Map results back to original offsets (the RUAccent backend normalises input); protect author marks
- [ ] User dictionary: YAML of forced readings, highest priority
- [ ] Engine presets selectable as targets (`--target yandex-speechkit`)
- [ ] Golden set `data/golden/ru.jsonl`: at least 300 homograph sentences from real scripts
- [ ] Evaluation harness: homograph accuracy, all-word accuracy, chars per second, posted as a PR comment
- [ ] Long input: sentence by sentence, constant memory

**Exit:** a real 30-minute script passes through the CLI, is voiced, and its stress-error count is recorded.

## Phase 2 — Web editor and API (2–3 weeks)

- [ ] FastAPI: `POST /v1/annotate`, version in every response, no text stored
- [ ] Single-screen, mobile-first editor: paste, see doubtful words, tap to switch, pick engine, copy
- [ ] One Docker container; hosting chosen at the start of the phase

**Exit:** a full episode prepared from a phone using only the web editor.

## Phase 3 — Open dataset (3–4 weeks)

- [ ] Example format, automatic checks, review queue, daily bot pull request
- [ ] Universal pack on decision lists: a correction changes results without retraining
- [ ] First numbered data release

**Exit:** a correction made in the editor changes the engine's answer within a day, visible in git history.

## Phase 4 — Distribution (2–3 weeks)

- [ ] PyPI package, npm client, MCP server
- [ ] LiveKit and Pipecat text transforms; presets for ElevenLabs, Yandex, Silero, OpenAI
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
