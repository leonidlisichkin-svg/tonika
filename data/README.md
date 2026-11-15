# Data

| Folder | Contents | Licence |
| --- | --- | --- |
| `examples/<lang>/` | Sentences with the correct reading of a word in context (JSONL) | CC0-1.0 |
| `golden/` | Held-out evaluation sets, never used for training (Phase 1) | CC0-1.0 |
| `lexicon/<lang>/` | Words and all their possible readings | Terms of each source, stated per file |

Examples and golden sets are dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/), so anyone, including TTS vendors,
can use them without conditions. Add only sentences you wrote yourself or took from a CC0 source.

Lexicon files derived from Wiktionary carry Wiktionary's licence (CC BY-SA 4.0) and attribution.
They live in their own folder so the licences never mix.

The record format is described in [`docs/DATA_SPEC.md`](../docs/DATA_SPEC.md).
