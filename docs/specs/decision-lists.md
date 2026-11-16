# Decision lists: the pack that learns from corrections

Status: specification for roadmap items 3.3 and 3.4. Changing it needs a `DECISIONS.md` entry.

## Why

A neural model cannot be corrected by a person: a wrong reading stays wrong until someone
retrains it. Decision lists close that gap. They are learnt from the open examples by counting,
in seconds, with no machine-learning dependency, and every decision can name its reason
("the word before is «на»"). A correction accepted today changes the answer tomorrow.

They serve two roles:

1. **Corrections layer** over a strong model (Russian): they override the model only where the
   examples are clear, and stay silent otherwise.
2. **Universal pack** for a language with examples but no model.

The method is the classic one for homograph disambiguation (Yarowsky, 1994): for each ambiguous
word, a list of context rules ordered by reliability; the first rule that matches decides.

## Training data

Accepted example records (`docs/DATA_SPEC.md`, section 1): a sentence, the position of one word,
its correct reading. Golden sets are never read by the trainer; the trainer refuses a path under
`data/golden/`.

## Features

For an example with target word at position 0 among the sentence's words (`text.iter_words`),
every word folded (`text.fold`: lower case, ё as е):

| Feature | Meaning |
| --- | --- |
| `w-1=<word>`, `w+1=<word>` | the word just before, just after |
| `w-2=<word>`, `w+2=<word>` | two before, two after |
| `b-=<w-2> <w-1>`, `b+=<w+1> <w+2>` | the pair before, the pair after |
| `in=<word>` | the word appears within three words on either side |
| `s-1=<end>`, `s+1=<end>` | the last three letters of the word before, after (grammar agreement) |
| `first`, `last` | the target opens, closes the sentence |
| `cap` | the target is capitalised and does not open the sentence |
| `p+1=<mark>` | the punctuation mark right after the target, if any |
| `ctx=<w-2> <w-1> _ <w+1> <w+2>` | the exact two words on each side; `^` and `$` stand for the sentence edge |

Except in `ctx`, a missing neighbour produces no feature. Feature strings are the stable identity
of a rule.

## Learning

For each folded form in the examples:

1. Count, for every feature, how often it occurs with each reading.
2. For each (feature, reading): `support` = its count; `precision` = `(support + α) / (total + 2α)`
   where `total` is the feature's count over all readings of this form.
3. **Memory rules.** Keep a `ctx` rule when it has never been contradicted (`total = support`),
   whatever its support. One accepted example is enough: the same words around the same word get
   the same reading.
4. **General rules.** Only for a form whose examples show at least two readings (a rule needs
   something to be compared with): keep any other rule when `support ≥ min_support` and
   `precision ≥ min_precision`.
5. Order: memory rules first, then by precision (high first), then support (high first), then
   feature string.

Defaults: `α = 0.5`, `min_support = 2`, `min_precision = 0.9`. With these, a general feature seen
twice, both times with the same reading, has precision 0.83 and is not kept; three times gives
0.875; four times, 0.9. One contradicting example needs thirteen agreeing ones to outweigh it.
That caution is deliberate: the layer must never make a good model worse on thin evidence. A
memory rule is safe on one example because it fires only on an identical context.

`default` for a form is its most frequent reading (ties: the lower reading index).

Everything is integer counting and sorting with fixed tie-breaks: the same examples always give
a byte-identical model file.

## Model file

`data/models/<lang>.dl.json`, JSON with sorted keys, two-space indent, trailing newline:

```json
{
  "format": "tonika-decision-lists/1",
  "lang": "ru",
  "data": "2027.01.1",
  "settings": {"alpha": 0.5, "min_precision": 0.9, "min_support": 2, "window": 3},
  "words": {
    "замок": {
      "readings": [{"stress": [1]}, {"stress": [3]}],
      "default": 1,
      "rules": [
        {"feature": "ctx=дверь на _ не закрывалась", "reading": 1, "support": 1, "precision": 0.75},
        {"feature": "w-1=на", "reading": 1, "support": 14, "precision": 0.967},
        {"feature": "s-1=ном", "reading": 0, "support": 9, "precision": 0.95}
      ]
    }
  }
}
```

`data` is the data release the examples came from. Precision is rounded to three decimals.

## The pack

`tonika.packs.decision_lists.DecisionListPack(lang, model_path)` implements `LanguagePack`.

- `model` is `dl-<lang>@<data>`, for example `dl-ru@2027.01.1`.
- `analyze(text)`: for every word whose folded form is in `words`, compute the features and take
  the first matching rule. The token gets that reading, the other readings as `alternatives`,
  `source: "rules"`, `confidence` = the rule's precision.
- No rule matches: used alone, the pack answers with `default` and no `confidence`; used as a
  layer, it stays silent.
- Tier: A (it knows which words are ambiguous).

## The layer

`tonika.packs.layered.LayeredPack(base, corrections)` implements `LanguagePack`.

- It runs `base.analyze(text)`, then asks `corrections` for decisions made by a rule (never by
  `default`).
- Where both have a token for the same span and the readings differ, the rule wins. The token
  keeps the base's reading among its `alternatives`.
- Where only the rule has a token, it is added. Where only the base has one, it stays.
- `model` is `<base model>+<corrections model>`, so every result names both.
- `get_pack(lang, "auto")` returns the layered pack when a model file for the language exists,
  else the base alone.

## Commands

```bash
tonika data train data/examples/ru --out data/models/ru.dl.json   # build the model
tonika data train data/examples/ru --report                       # cross-validated quality
```

`--report` runs 5-fold cross-validation with a fixed split (fold = example index mod 5 after
sorting by id) and prints, per form and in total: examples, rules, coverage (share decided by a
rule) and precision of those decisions.

## Gates

- CI evaluates the layered pack on the golden set. It must score at least the base pack's
  accuracy; a model file that lowers it does not merge.
- Rebuilding the model file in CI from the committed examples must reproduce the committed file.

## Acceptance tests

1. Counting and thresholds: a hand-made set of examples gives exactly the expected rules, in the
   expected order, with the expected numbers (include the 2, 3 and 4 agreeing cases above).
2. Determinism: shuffling the examples gives a byte-identical file.
3. Each feature kind has a test where only that feature decides.
4. `DecisionListPack` alone: rule decision with `confidence`; fallback to `default` without it.
5. `LayeredPack`: rule overrides base; base kept where no rule; base reading preserved in
   `alternatives`; `model` names both.
6. The trainer refuses `data/golden/`.
7. A memory rule: one example fixes the same five-word context and nothing else; a second example
   with the same context and another reading removes the rule.
8. End to end, with `FakePack` as base: a wrong reading is fixed in its own context by one
   accepted example, and in new sentences by four examples that share a feature. This is the
   proof of the Phase 3 exit criterion.
