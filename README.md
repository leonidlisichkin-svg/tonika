# Tonika

**An open pronunciation layer for any TTS engine.**

[![CI](https://github.com/leonidlisichkin-svg/tonika/actions/workflows/ci.yml/badge.svg)](https://github.com/leonidlisichkin-svg/tonika/actions/workflows/ci.yml)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/leonidlisichkin-svg/tonika)

Text-to-speech engines guess. In Russian, *замок* is a castle (за́мок) or a lock (замо́к), and only
the sentence tells you which. Tonika reads the context, decides how each word should sound, and
hands your TTS engine the text in the notation it understands.

```bash
$ tonika annotate --target yandex-speechkit "В старом замке сломался замок."
В старом з+амке сломался зам+ок.
```

> **Status: Phase 1, the Russian core.** Russian works from the command line and from Python:
> context-aware stress for homographs, ё restored, long scripts, a user dictionary, engine presets.
> Accuracy on our golden set of 377 hard words (homographs and ё only): **92.3%**, measured in CI
> on every pull request. Not on PyPI yet. Next: the web editor. See the [roadmap](docs/ROADMAP.md).

## Why

- **Context, not a dictionary.** A dictionary knows both readings of *замок*; only context picks one.
- **One analysis, any engine.** Tonika separates *what* to say from *how* to mark it. The same
  result renders as `за́мок`, `з+амок` or `зАмок`, whichever your engine reads.
- **The author has the last word.** Stress you typed yourself and your own dictionary always win.
- **Open data anyone can fix.** The examples that teach the engine are public (CC0) and editable,
  like Wikipedia for pronunciation.
- **Local-first.** A library that runs offline in your process, fast enough for voice agents.

## Install

```bash
git clone https://github.com/leonidlisichkin-svg/tonika && cd tonika
uv sync --extra ru        # the Russian pack; models (about 500 MB) download on first use
```

Without `--extra ru` Tonika runs on a tiny demo pack and says so.

## Use it

A whole script, for a given engine, with your names, and a list of words worth a second look:

```bash
uv run tonika annotate -f script.txt -o marked.txt \
    --target yandex-speechkit --dict names.txt --review check.md
```

From Python:

```python
from tonika import annotate, analyze

annotate("В старом замке сломался замок.", target="plus")
# 'В старом з+амке сломался зам+ок.'

doc = analyze("В старом замке сломался замок.")
print(doc.to_json())  # the Intent Document: every decision and the readings it rejected
```

| Notation | Example | For |
| --- | --- | --- |
| `acute` | за́мок | the Unicode standard (U+0301) |
| `plus` | з+амок | Yandex SpeechKit, Silero |
| `upper` | зАмок | engines that ignore accent marks |
| `yo` | всё | restore ё only, no stress marks |

- **Targets.** `--target` takes a notation or an engine preset; `tonika engines` lists the presets.
- **Modes.** `ambiguous` (default) marks only words that could be read another way; `all` marks
  every word; `yo` restores ё only.
- **Your marks.** Stress already typed in the text (`зам+ок` or `замо́к`) is kept and converted to
  the target notation.
- **Your dictionary.** One entry per line: `+Окленд`, `Верещ+агин*`,
  `JW Marriott = Джей-Д+абл-ю М+арриотт`. See [docs/DICTIONARY.md](docs/DICTIONARY.md).
- **Other languages.** Ukrainian, Belarusian and others get dictionary stress without context
  (tier B) through the same backend. Only Russian is measured so far.

## Develop

Open the repository in a GitHub Codespace (the badge above): Python, uv and the models are set up
for you. Or locally:

```bash
uv sync
uv run pytest -m "not models"
```

Read [CONTRIBUTING.md](CONTRIBUTING.md). Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Licence

Code: [Apache-2.0](LICENSE). Examples, dictionaries and engine presets: CC0-1.0. Third-party
components: [LICENSES.md](LICENSES.md).

---

**По-русски.** Tonika — открытый слой произношения между текстом и любым синтезатором речи.
Она по контексту решает, как читать слово (за́мок или замо́к), возвращает ё и отдаёт текст в
разметке, которую понимает ваш TTS. Ваши собственные ударения и ваш словарь всегда главнее модели.
Данные открыты, исправить ударение может любой.
