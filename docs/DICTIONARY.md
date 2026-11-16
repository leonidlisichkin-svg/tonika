# User dictionary

A user dictionary fixes the reading of words the language pack cannot know: names, places,
brands, invented words. It is a plain text file, one entry per line, and it always wins over the
language pack. Stress marks typed in the text itself win over the dictionary.

```bash
tonika annotate -f script.txt --dict names.txt --target yandex-speechkit
```

```python
annotate(text, dictionary="names.txt")
```

`--dict` may be given several times; later files override earlier ones.

## Entries

| Entry | Meaning |
| --- | --- |
| `+Окленд` | Stress: put `+` before the stressed vowel. A combining acute after the vowel works too. |
| `Верещ+агин*` | `*` also matches longer forms of one word: Верещагина, Верещагину. |
| `Корол+ёв` | Restores ё: matches «Королев» in the text and reads it as «Королёв». |
| `Н+овая Зел+андия` | A phrase. Every word that needs a mark gets one. |
| `JW Marriott = Джей-Д+абл-ю М+арриотт` | Replacement: the engine reads the right-hand side. |

Rules:

- Text after `#` is a comment. Empty lines are ignored.
- Matching ignores letter case and treats ё and е as the same letter.
- An entry matches whole words only: `+Окленд` does not match «Оклендский» unless it ends in `*`.
- When several entries match at the same place, the longest wins.
- An entry without a stress mark is an error; Tonika names the file and the line.

A dictionary reading is marked in every mode, including `ambiguous`, because the author chose it.
In the Intent Document such tokens have `"source": "user"`.

A working example: [`data/dictionaries/example.txt`](../data/dictionaries/example.txt).
