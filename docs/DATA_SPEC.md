# Data specification

Three layers of data, each with its own licence. See [`data/README.md`](../data/README.md).

## 1. Examples — `data/examples/<lang>/*.jsonl` (CC0-1.0)

One JSON object per line: a sentence, the position of one word, and its correct reading.

```json
{"id": "ru-000001", "lang": "ru", "text": "Дверь заперта на замок.", "start": 17, "end": 22, "form": "замок", "reading": {"stress": [3]}, "status": "accepted", "votes": 3, "license": "CC0-1.0"}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | `<lang>-<six digits>`, never reused |
| `lang` | string | BCP-47 tag |
| `text` | string | One sentence, NFC |
| `start`, `end` | integer | Code-point offsets of the word in `text` |
| `form` | string | Must equal `text[start:end]` |
| `reading` | object | Same shape as `reading` in the Intent Document |
| `status` | string | `proposed`, `accepted` or `rejected` |
| `votes` | integer | Independent confirmations |
| `license` | string | Always `CC0-1.0` |

Rules: the sentence is your own or comes from a CC0 source; one target word per record; several
records may share a sentence.

## 2. Golden sets — `data/golden/<lang>.jsonl` (CC0-1.0, Phase 1)

Same record format as examples. Never used for training. A release is blocked if accuracy on its
golden set drops.

## 3. Lexicon — `data/lexicon/<lang>/` (terms of each source)

Every word with all its readings and a short gloss, so the editor can explain each choice.

```json
{"lang": "ru", "form": "замок", "readings": [{"id": "замок.castle", "stress": [1], "gloss": "крепость"}, {"id": "замок.lock", "stress": [3], "gloss": "запор"}], "source": "wiktionary", "license": "CC BY-SA 4.0"}
```

Files derived from Wiktionary keep its licence and attribution and stay in their own folder.

## Contribution flow (Phase 3)

1. An author fixes a reading in the editor and submits it.
2. Automatic checks: the word is in the sentence, the stress falls on a vowel, the reading is
   known to the lexicon or flagged as new.
3. Accepted after three independent confirmations or one language editor.
4. A bot batches accepted changes into a daily pull request; history and authorship stay in git.
5. Every data release gets a version number; engine and models cite the release they use.

## Disputed norms

When both readings are correct (тво́рог / творо́г), both are recorded as correct and the language
editor chooses the default.
