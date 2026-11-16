# Accuracy of the Russian models

Every model id of stressonnx 0.0.2 that serves `ru`, measured on 2026-11-16 in a GitHub
Codespace: 2 cores (AMD EPYC 7763, x86-64-v3), 8 GB, Python 3.13.18, onnxruntime 1.32.0.
stressonnx has no stable 0.0.3 yet (only pre-releases `0.0.3a*`, which we do not pin), so these
three are all there are. CI measures only the default model.

```bash
uv run tonika eval data/golden/ru.txt --pack stressonnx:<id> --format json
uv run tonika trial data/trials/ru/chekhov-lady-with-the-dog.txt --pack stressonnx:<id> --format json
```

| Model id | Golden set (377 words) | Left unmarked | Trial text preserved | Words given stress | To review per 1,000 words | ё restored | Speed on the trial | Peak memory | Download | Licence (registry) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`ruaccent`** (default) | **92.3%** (348) | 0 | yes | 3,183 | 60.9 | 157 | 542 chars/s | 696 MiB | 478 MB | Apache-2.0 |
| `silero` | 9.8% (37) | 319 | yes | 3,096 | 0.0 | 145 | 69,690 chars/s | 109 MiB | 8.7 MB | MIT |
| `simple` | 23.1% (87) | 207 | yes | 815 | 0.0 | 0 | 193,414 chars/s | 82 MiB | 0.4 MB | MIT |

How to read it:

- The golden set holds only hard words: homographs and ё. `silero` and `simple` leave most of
  them unmarked (319 and 207 of 377), because they do not resolve homographs by context.
- "To review" is zero for `silero` and `simple` because the pack learns a word's other readings
  only from `ruaccent`'s homograph tables. A zero there means "does not know", not "sure".
- Download is the size of the model files in the Hugging Face cache. Peak memory is the whole
  process, from the trial report.
- Speed differs between machines by up to four times; compare within this table only.

**Choice: `ruaccent` stays the default** (D-022). It is 69 percentage points ahead, so the
tie-breakers (words to review, speed, size) do not apply. The floor in
`data/golden/baseline.json` stays at 0.90: accuracy did not change.

Found while measuring, left for its own pull request: `StressonnxPack` reports tier A for Russian
whatever the model, so with `--pack stressonnx:silero` or `stressonnx:simple` the default mode
`ambiguous` marks no word at all. Those models should report tier B, whose default mode is `all`.
