# Licences

| Part | Licence |
| --- | --- |
| Source code (`src/`, `tests/`, tooling) | [Apache-2.0](LICENSE) |
| Examples and golden sets (`data/examples/`, `data/golden/`) | CC0-1.0 |
| Example dictionaries (`data/dictionaries/`) | CC0-1.0 |
| Engine presets (`src/tonika/engines/*.toml`) | CC0-1.0 |
| JSON Schema (`spec/`) | CC0-1.0 |
| Lexicon files (`data/lexicon/`) | Terms of each source, stated in each file |
| Trial texts (`data/trials/`) | Public domain; source and reason per file in `data/trials/README.md` |

## Third-party components

Nothing third-party is bundled in the Tonika wheel. The only third-party content stored in this
repository is the public-domain trial text in `data/trials/`. The Russian pack installs its
backend as an optional extra, and the backend downloads its models on first use.
Every component must be listed here **before** it is used. Non-commercial licences are not allowed.

| Component | Use | Licence | Status |
| --- | --- | --- | --- |
| [stressonnx](https://pypi.org/project/stressonnx/) 0.0.2 | Russian pack backend, optional extra `ru` | Apache-2.0 | In use, pinned |
| RUAccent models (downloaded by stressonnx from `TigreGotico/stressonnx-models`) | Russian stress, homographs, ё | Apache-2.0 | In use |
| onnxruntime, numpy, huggingface_hub, tokenizers (dependencies of stressonnx) | Model runtime | MIT, BSD-3-Clause, Apache-2.0, Apache-2.0 | In use with extra `ru` |
| FastAPI, Starlette, pydantic, pydantic-core, uvicorn | HTTP API, optional extra `api` | MIT, BSD-3-Clause, MIT, MIT, BSD-3-Clause | In use with extra `api` |
| anyio, annotated-types, annotated-doc, typing-inspection, h11, click, idna (dependencies of the above) | HTTP API runtime | MIT, MIT, MIT, MIT, MIT, BSD-3-Clause, BSD-3-Clause | In use with extra `api` |
| opentelemetry-api (a dependency of FastAPI) | Tracing interface only; sends nothing without an SDK, which Tonika does not install | Apache-2.0 | In use with extra `api` |
| silero_stress vocabularies (via stressonnx) | Ukrainian, Belarusian and other languages, tier B | MIT | Available, not yet evaluated |
| Wiktionary | Lexicon source | CC BY-SA 4.0 | Planned, own folder |
| A. P. Chekhov, «Дама с собачкой» (1899), text via Russian Wikisource | Trial text `data/trials/ru/` | Public domain (author died 1904; published 1899) | In use; Wikisource notes removed |
| Silero TTS models | Not used | CC BY-NC 4.0 | Excluded; only its notation is described in `src/tonika/engines/silero.toml` |

Dev-only tools (pytest, ruff, mypy, jsonschema, httpx with httpcore and certifi) are not
distributed with Tonika.
