# Trials

A trial runs a long text through the whole pipeline with `tonika trial` and records what it
cost. It proves one thing with certainty: the text comes out changed only by pronunciation marks
and ё. For every notation (`acute`, `plus`, `upper`, `yo`) and every mode (`ambiguous`, `all`,
`yo`), the output is undone using only the Intent Document (the marks at the letters it
stresses, the respellings it records) and must give the input back character for character:
every space, line break, punctuation mark and letter case. It does not measure whether the
stresses are right; accuracy is measured on the golden set (`tonika eval`).

```bash
uv run tonika trial data/trials/ru/chekhov-lady-with-the-dog.txt
```

CI runs the same command in the `models` job on every pull request, posts the table in the pull
request comment and fails when the text is not preserved. Speed and memory are recorded, never
asserted: they depend on the machine.

What the numbers mean:

- **Words** are runs of letters, so «кто-то» counts as two.
- **Words given stress** carry a stress decision: what `--mode all` marks. Words with one vowel
  get none.
- **Words with more than one reading** are what `--review` lists for a human to check, and what
  the default mode `ambiguous` marks.
- **ё restored** counts words in which an е became ё («ее» → «её»).
- **Speed** is analysis only, after the models are loaded.
- **Peak memory** is the resident memory of the whole process at its peak, models included.

## 2026-11-16 · Chekhov, «Дама с собачкой» · stressonnx 0.0.2

Text: `data/trials/ru/chekhov-lady-with-the-dog.txt`, about 34 minutes of speech; source and
licence in `data/trials/README.md`. Machine: GitHub Codespace, 2 cores (AMD EPYC 7763), 8 GB,
Python 3.13.18, onnxruntime 1.32.0. Two runs gave the same output and the same counts; speed
was 541 characters per second both times, peak memory 687 and 660 MiB.

| Metric | Value |
| --- | --- |
| Text preserved | yes, in all 4 notations × 3 modes |
| Characters | 31,075 |
| Words | 5,156 |
| Words given stress (marked by `--mode all`) | 3,183 (61.7%) |
| Words with more than one reading (listed by `--review`) | 314: 60.9 per 1,000 words |
| ё restored | 157 |
| Speed | 541 characters per second (57.4 s for the text) |
| Peak memory | 660 MiB (whole process) |
| Pack | `stressonnx-0.0.2:ruaccent@b8ba7afd` |

The same day in CI (pull request #5, GitHub-hosted runner, image ubuntu-26.04, Python 3.13.18,
the same locked dependencies): text preserved; 3,181 words given stress; 314 to review; 157 ё
restored; 2,310 characters per second; 699 MiB.

Findings:

- Nothing in the text changed except marks and ё: no lost space, line break, non-breaking space,
  dash or capital letter. No bug was found in the pipeline, so this trial brought no fix.
- **Same model, different machine, slightly different answer.** CI gave stress to 3,181 words,
  the Codespace to 3,183, with the same model string and locked dependencies. On one machine the
  result is stable: two runs agree, and so do one core and two cores. The likely cause is the
  processor: onnxruntime picks different arithmetic kernels on different CPUs, which can tip a
  close decision. This touches principle 4 (deterministic output) and is left for its own pull
  request: save the Intent Document from both machines, find the two words, then decide whether
  to pin onnxruntime's behaviour or to state determinism per machine.
- The review load is about one word in sixteen: a 30-minute text gives a checklist of some 300
  words. That is the number to bring down in Phase 3 (corrections layer) and to show well in the
  Phase 2 review flow.
- Analysing 30 minutes of speech takes about a minute on a 2-core machine, after a model load.

Found outside the pipeline: `tonika annotate -f` and standard input read text with Python's
default newline handling, so a file with Windows line endings (CR LF) comes out with LF only.
The pipeline itself keeps CR LF (`tonika trial` reads files as they are, and a test covers it).
Harmless for speech, but it is a change to the text; left for its own pull request.
