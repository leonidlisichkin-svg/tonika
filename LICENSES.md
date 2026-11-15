# Licences

| Part | Licence |
| --- | --- |
| Source code (`src/`, `tests/`, tooling) | [Apache-2.0](LICENSE) |
| Examples and golden sets (`data/examples/`, `data/golden/`) | CC0-1.0 |
| Engine presets (`engines/`) | CC0-1.0 |
| JSON Schema (`spec/`) | CC0-1.0 |
| Lexicon files (`data/lexicon/`) | Terms of each source, stated in each file |

## Third-party components

Nothing third-party is bundled yet. Every component must be listed here **before** it is used.
Non-commercial licences are not allowed.

| Component | Use | Licence | Status |
| --- | --- | --- | --- |
| [stressonnx](https://pypi.org/project/stressonnx/) | Russian pack backend (Phase 1), optional extra `ru` | Apache-2.0 | Planned |
| RUAccent models (via stressonnx) | Russian stress and homographs | Apache-2.0 | Planned |
| silero_stress vocabularies (via stressonnx) | Ukrainian, Belarusian, other vocabularies | MIT | Planned |
| Wiktionary | Lexicon source | CC BY-SA 4.0 | Planned, own folder |
| Silero TTS models | Not used | CC BY-NC 4.0 | Excluded; only its notation is described in `engines/silero.yaml` |

Dev-only tools (pytest, ruff, mypy, jsonschema, PyYAML) are not distributed with Tonika.
