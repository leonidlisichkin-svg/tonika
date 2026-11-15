# CLAUDE.md — standing instructions for Tonika

Tonika is an open pronunciation layer between text and any TTS engine. Input: plain text.
Output: the same text, marked so the engine reads it as the author intended. We start with
Russian word stress and ё. Vision: `docs/VISION.md`. Plan: `docs/ROADMAP.md`.

## How to work with Leo (the maintainer)

- Talk to him in Russian. Write code, docs and commit messages in English.
- He works from a phone, with no local machine. Everything must be verifiable through GitHub
  Actions and pull request comments.
- One session = one small pull request with green CI.
- Start every session by reading this file and `docs/ROADMAP.md`. Take the next unchecked item of
  the current phase. If it is too big for one pull request, propose a split and wait.
- If the plan conflicts with reality (a package API, a licence, a name), stop and say so.
- Record every decision that changes the plan in `docs/DECISIONS.md`.
- End every session with three lines: what changed, CI status, the next unchecked ROADMAP item.
- Ask before adding any new service, account, paid dependency or runtime dependency.

## Principles (non-negotiable)

1. Analysis and rendering are separate. Analysis produces an Intent Document
   (`spec/intent-document.schema.json`); renderers turn it into text. Never mix the two.
2. Language packs are plugins behind `tonika.packs.base.LanguagePack`. Do not write stress
   models from scratch; wrap the best open ones. Every backend must be swappable.
3. Local-first: the library works offline in the user's process. Any API is a thin wrapper.
4. Deterministic: same text and same model version give the same output. Every result names its
   model and data version.
5. Stress marks already in the input are the author's intent. Preserve them.
6. Offsets are code-point indices into the NFC-normalised input.
7. Licence hygiene. Code: Apache-2.0. Examples and engine presets: CC0-1.0. Wiktionary-derived
   lexicon: its own folder, under its source terms. Record every third-party model and dataset in
   `LICENSES.md` before using it. Never add anything non-commercial.
8. No secrets in the repository.

## Commands

```bash
uv sync                                    # install with dev tools
uv run ruff check src tests                # lint
uv run ruff format src tests               # format
uv run mypy                                # strict type check of src/
uv run pytest -m "not models"              # offline tests (the default everywhere)
uv run pytest -m models                    # tests that download real models
uv run tonika annotate --target plus "В старом замке сломался замок."
```

## Testing rules

- Unit tests run offline with no model downloads. Use `FakePack` (`pack="fake"`).
- Tests that need real models carry `@pytest.mark.models` and run only in the GitHub Actions
  `models` job. The Claude Code cloud environment cannot reach Hugging Face by default.
- Every bug fix comes with a test that fails without the fix.

## Layout

```
src/tonika/document.py   Intent Document: dataclasses, validation, JSON
src/tonika/text.py       NFC, word finding, author-mark detection, case matching
src/tonika/packs/        LanguagePack protocol, registry, FakePack
src/tonika/render.py     notations (acute, plus, upper, yo) and modes (ambiguous, all, yo)
src/tonika/pipeline.py   analyze() and annotate(), the public entry points
src/tonika/cli.py        `tonika annotate`
spec/                    JSON Schema of the Intent Document
engines/                 TTS engine presets (CC0), one YAML per engine
data/                    examples, golden sets, lexicons (see data/README.md)
docs/                    vision, architecture, data spec, roadmap, decisions
```

## Conventions

- Python 3.11+, `from __future__ import annotations`, full type hints, mypy strict.
- Public API lives in `tonika/__init__.py`. Keep it small.
- The core has no runtime dependencies. Language packs bring their own as optional extras.
- Commit messages: imperative mood, one line under 72 characters, details in the body.
