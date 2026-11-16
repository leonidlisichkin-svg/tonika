# Data

| Folder | Contents | Licence |
| --- | --- | --- |
| `golden/` | Held-out evaluation sets and the accuracy floor. Never used for training | CC0-1.0 |
| `examples/<lang>/` | Sentences with the correct reading of a word in context (JSONL, Phase 3) | CC0-1.0 |
| `dictionaries/` | Example user dictionaries | CC0-1.0 |
| `lexicon/<lang>/` | Words and all their possible readings | Terms of each source, stated per file |

Examples and golden sets are dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/), so anyone, including TTS vendors,
can use them without conditions. Add only sentences you wrote yourself or took from a CC0 source.

Lexicon files derived from Wiktionary carry Wiktionary's licence (CC BY-SA 4.0) and attribution.
They live in their own folder so the licences never mix.

## Golden sets

`golden/ru.txt` holds one sentence per line with the tested words marked by `+` before the
stressed vowel; `#` starts a comment. Check a language pack against it:

```bash
uv run tonika eval data/golden/ru.txt --baseline data/golden/baseline.json
```

`golden/baseline.json` is the lowest accuracy CI accepts for each language.

The record formats are described in [`docs/DATA_SPEC.md`](../docs/DATA_SPEC.md).
