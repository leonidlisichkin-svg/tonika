# CLAUDE.md — standing instructions for Tonika

Tonika is an open pronunciation layer between text and any TTS engine. Input: plain text.
Output: the same text, marked so the engine reads it as the author intended. We start with
Russian word stress and ё. Vision: `docs/VISION.md`. Plan: `docs/ROADMAP.md`.

## How to work with Leo (the maintainer)

- Talk to him in Russian. Write code, docs and commit messages in English.
- He works in a GitHub Codespace (VS Code in the browser) from a work computer and keeps nothing
  on a local machine. The environment is defined in `.devcontainer/`; see `docs/CODESPACES.md`.
  Everything must be verifiable through GitHub Actions and pull request comments.
- Give him one concrete step at a time, with no technical shorthand: which button and where it is
  on the screen, which key to press, the exact line to paste. Explain results in plain words,
  ask for a screenshot, and wait for his answer before the next step.
- Two roles. A Claude chat outside this repository (the conductor) holds the strategy with Leo
  and writes briefs. You, in the Codespace, carry them out. When Leo pastes a brief from the
  conductor, save it under `docs/briefs/` in the same pull request and follow it like any other
  brief. If it conflicts with this file, the code or the roadmap, say so before building.
- One session = one small pull request with green CI. Branch from an up-to-date `main`, never push
  to `main`. Leo merges: tell him the exact button.
- Start every session by reading this file and `docs/ROADMAP.md`. Take the next unchecked item of
  the current phase and follow its brief in `docs/briefs/`. If the item has no brief, the session's
  pull request is the brief. If it is too big for one pull request, propose a split and wait.
- If the plan conflicts with reality (a package API, a licence, a name), stop and say so.
- Record every decision that changes the plan in `docs/DECISIONS.md`.
- End every session with three lines: what changed, CI status, the next unchecked ROADMAP item.
  Leo carries these lines back to the conductor, so they must stand on their own: name the pull
  request, any decision recorded, and anything that now needs his or the conductor's decision.
- Ask before adding any new service, account, paid dependency or runtime dependency.

## Principles (non-negotiable)

1. Analysis and rendering are separate. Analysis produces an Intent Document
   (`spec/intent-document.schema.json`); renderers turn it into text. Never mix the two.
2. Language packs are plugins behind `tonika.packs.base.LanguagePack`. Do not write stress
   models from scratch; wrap the best open ones. Every backend must be swappable.
3. Local-first: the library works offline in the user's process. Any API is a thin wrapper.
4. Deterministic: same text and same model version give the same output. Every result names its
   model and data version.
5. Stress marks already in the input are the author's intent. Keep their reading; change only
   their notation to the target's.
6. Offsets are code-point indices into the NFC-normalised input.
7. Licence hygiene. Code: Apache-2.0. Examples, dictionaries and engine presets: CC0-1.0.
   Wiktionary-derived lexicon: its own folder, under its source terms. Record every third-party
   model and dataset in `LICENSES.md` before using it. Never add anything non-commercial.
8. No secrets in the repository.
9. The golden set (`data/golden/`) is held out. Never train on it and never write a rule for one
   of its sentences. Accuracy on it must not fall: the floor is `data/golden/baseline.json`.
   Raise the floor when accuracy rises; lowering it needs an entry in `docs/DECISIONS.md`.

## Commands

```bash
uv sync                                    # install with dev tools (offline demo pack only)
uv sync --extra ru                         # also install the real Russian pack (stressonnx)
uv run ruff check src tests                # lint
uv run ruff format src tests               # format
uv run mypy                                # strict type check of src/
uv run pytest -m "not models"              # offline tests (the default everywhere)
uv run pytest -m models                    # tests with real models (needs --extra ru)
uv run tonika annotate --target plus "В старом замке сломался замок."
uv run tonika annotate -f script.txt --target yandex-speechkit --dict names.txt --review check.md
uv run tonika eval data/golden/ru.txt --baseline data/golden/baseline.json
uv run tonika engines                      # list engine presets
```

## Testing rules

- Unit tests run offline with no model downloads. Use `FakePack` (`pack="fake"`) or a
  `ScriptedBackend` from `tests/helpers.py`.
- Tests that need real models carry `@pytest.mark.models`. They run in the GitHub Actions `models`
  job and in a Codespace (first use downloads about 500 MB from Hugging Face). The Claude Code
  cloud sandbox at claude.ai/code cannot reach Hugging Face by default.
- The `models` job posts accuracy on the golden set as a pull request comment and fails below the
  floor. Quote that number when a change touches a language pack.
- Every bug fix comes with a test that fails without the fix.

## Layout

```
src/tonika/document.py     Intent Document: dataclasses, validation, JSON
src/tonika/text.py         NFC, word finding, author marks, case matching, mark location
src/tonika/segment.py      sentence chunks for long input
src/tonika/packs/          LanguagePack protocol, registry, FakePack, StressonnxPack
src/tonika/dictionary.py   user dictionary of forced readings (plain text)
src/tonika/render.py       notations (acute, plus, upper, yo) and modes (ambiguous, all, yo)
src/tonika/engines/        TTS engine presets (CC0), one TOML per engine
src/tonika/pipeline.py     analyze() and annotate(), the public entry points
src/tonika/review.py       checklist of ambiguous words for a human
src/tonika/evaluate.py     accuracy on marked examples
src/tonika/cli.py          `tonika annotate`, `tonika eval`, `tonika engines`
spec/                      JSON Schema of the Intent Document
data/                      golden sets, examples, dictionaries, lexicons (see data/README.md)
docs/                      vision, architecture, roadmap, decisions
docs/specs/                contracts for upcoming work
docs/briefs/               one ready task per pull request
.devcontainer/             the Codespace: Python, uv, Node, Claude Code
```

## Conventions

- Python 3.11+, `from __future__ import annotations`, full type hints, mypy strict.
- Public API lives in `tonika/__init__.py`. Keep it small.
- The core has no runtime dependencies. Language packs bring their own as optional extras.
- Commit messages: imperative mood, one line under 72 characters, details in the body.
