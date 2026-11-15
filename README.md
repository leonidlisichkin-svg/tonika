# Tonika

**An open pronunciation layer for any TTS engine.**

Text-to-speech engines guess. In Russian, *замок* is a castle (за́мок) or a lock (замо́к), and only
the sentence tells you which. Tonika reads the context, decides how each word should sound, and
hands your TTS engine the text in the notation it understands.

```bash
$ tonika annotate --target plus "В старом замке сломался замок."
В старом з+амке сломался зам+ок.
```

> **Status: Phase 0, foundation.** The core, the Intent Document, the renderers and the CLI work.
> Language packs are not shipped yet: the command above runs on a small demo pack. The real Russian
> pack arrives in Phase 1. See the [roadmap](docs/ROADMAP.md).

## Why

- **Context, not a dictionary.** A dictionary knows both readings of *замок*; only context picks one.
- **One analysis, any engine.** Tonika separates *what* to say from *how* to mark it. The same
  result renders as `за́мок`, `з+амок` or `зАмок`, whichever your engine reads.
- **Open data anyone can fix.** The examples that teach the engine are public (CC0) and editable,
  like Wikipedia for pronunciation.
- **Local-first.** A library that runs offline in your process, fast enough for voice agents.

## Use it

```python
from tonika import annotate, analyze

annotate("В старом замке сломался замок.", lang="ru", target="plus")
# 'В старом з+амке сломался зам+ок.'

doc = analyze("В старом замке сломался замок.", lang="ru")
print(doc.to_json())  # the Intent Document: every decision, its alternatives and confidence
```

| Notation | Example | For |
| --- | --- | --- |
| `acute` | за́мок | the Unicode standard (U+0301) |
| `plus` | з+амок | Yandex SpeechKit, Silero |
| `upper` | зАмок | engines that ignore accent marks |
| `yo` | всё | restore ё only, no stress marks |

Modes: `ambiguous` (default) marks only words that could be read another way; `all` marks every
word; `yo` restores ё only. Engine notes live in [`engines/`](engines/).

## Develop

```bash
uv sync
uv run pytest -m "not models"
```

Read [CONTRIBUTING.md](CONTRIBUTING.md). Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Licence

Code: [Apache-2.0](LICENSE). Examples and engine presets: CC0-1.0. Third-party components:
[LICENSES.md](LICENSES.md).

---

**По-русски.** Tonika — открытый слой произношения между текстом и любым синтезатором речи.
Она по контексту решает, как читать слово (за́мок или замо́к), и отдаёт текст в разметке, которую
понимает ваш TTS. Данные открыты, исправить ударение может любой.
