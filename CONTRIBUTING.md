# Contributing to Tonika

Thank you. Tonika gets better with every corrected word.

## Ways to help

- **Report a wrong reading.** Open an issue with the sentence, the word, and the correct reading.
- **Verify an engine.** Test which notation a TTS engine honours and update its file in
  `src/tonika/engines/` (set `verified_by` to your GitHub handle and `verified_on` to today).
- **Add examples.** From Phase 3 the web editor submits them for you. Until then, open a pull
  request to `data/examples/<lang>/` following [`docs/DATA_SPEC.md`](docs/DATA_SPEC.md).
- **Write code.** Pick an unchecked item in [`docs/ROADMAP.md`](docs/ROADMAP.md) and open an issue
  first so we agree on the approach.

## Licensing of contributions

- Code you contribute is licensed under Apache-2.0.
- Examples, golden sets and engine presets you contribute are dedicated to the public domain under
  CC0-1.0. Submit only sentences you wrote yourself or took from a CC0 source.

## Development

The quickest way in is a GitHub Codespace: **Code → Codespaces → Create codespace on main**.
Everything below is already installed there. See [`docs/CODESPACES.md`](docs/CODESPACES.md).

```bash
uv sync
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest -m "not models"
```

- Keep pull requests small, with tests. CI must be green.
- Unit tests must run offline; use the demo pack (`pack="fake"`). Tests that download models carry
  `@pytest.mark.models`.
- A change to a language pack must not lower accuracy on the golden set. CI posts the number on
  the pull request. Never tune code to the golden sentences.
- A change to the plan needs a new entry in [`docs/DECISIONS.md`](docs/DECISIONS.md).

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
