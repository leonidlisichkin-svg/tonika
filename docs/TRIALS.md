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
- **Processor** is the CPU and its x86-64 level as `/proc/cpuinfo` reports them ("unknown"
  elsewhere). The level says which arithmetic kernels onnxruntime can use: v3 has AVX2, v4 adds
  AVX-512.
- **Digest** is a SHA-256 of the Intent Document's tokens: two runs with the same digest made
  the same decision for every word.
- **Against the reference** compares with `data/trials/reference.json`, the Codespace run of the
  same model. CI fails when words given stress differ from it by more than 0.1% (D-021).

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
restored; 2,310 characters per second; 699 MiB. A second CI run, on a slower runner (770
characters per second, 697 MiB), gave 3,183 words given stress, as in the Codespace.

Findings:

- Nothing in the text changed except marks and ё: no lost space, line break, non-breaking space,
  dash or capital letter. No bug was found in the pipeline, so this trial brought no fix.
- **Same model, different machine, slightly different answer.** One CI runner gave stress to
  3,181 words; another CI runner and the Codespace gave 3,183, with the same model string and
  locked dependencies. On one machine the result is stable: two runs agree, and so do one core
  and two cores. Traced to its two words in the next trial; the rule is D-021.
- The review load is about one word in sixteen: a 30-minute text gives a checklist of some 300
  words. That is the number to bring down in Phase 3 (corrections layer) and to show well in the
  Phase 2 review flow.
- Analysing 30 minutes of speech takes about a minute on a 2-core machine, after a model load.

Found outside the pipeline: `tonika annotate -f` and standard input read text with Python's
default newline handling, so a file with Windows line endings (CR LF) comes out with LF only.
The pipeline itself keeps CR LF (`tonika trial` reads files as they are, and a test covers it).
Harmless for speech, but it is a change to the text. Fixed in the next trial's pull request.

## 2026-11-16 · Drift traced to two words · pull request #6

CI now saves the trial's Intent Document as a workflow artifact and names the processor. The
first CI run of pull request #6 landed on a runner that drifts, and its document was compared
with the Codespace's word by word.

| | Codespace | CI runner |
| --- | --- | --- |
| Processor | AMD EPYC 7763, x86-64-v3 | Intel Xeon 6975P-C, x86-64-v4 (avx512_vnni, avx512_bf16, avx_vnni, amx_tile) |
| Words given stress | 3,183 | 3,181 |
| Digest | `2aaddee3ff094ce7…` | `187285c3dcc117b7…` |
| Speed | 542 characters per second | 1,229 characters per second |

The two words, both stressed correctly in the Codespace and left with no stress mark at all on
the CI runner (the model judged that they need none):

| Word | Sentence (shortened) | Codespace | CI runner |
| --- | --- | --- | --- |
| победах (character 2,892) | …ему вспомнились эти рассказы о легких **победах**, о поездках в горы… | поб+едах | победах (no mark) |
| тайне (character 27,549) | Каждое личное существование держится на **тайне**, и, быть может… | т+айне | тайне (no mark) |

Nothing else differs: same tokens, same readings, same alternatives. The drift is 2 of 3,183
words given stress, 0.063%. The three CI runs of pull request #5 gave 3,183 twice and 3,181
once; their processors were not recorded then. A later CI run of pull request #6 landed on an
AMD EPYC 7763 runner, the Codespace's processor, and gave the reference digest exactly.

A fix was looked for and not found. stressonnx 0.0.2 creates its onnxruntime sessions with no
session options, and `make_stressor` accepts only the model, the language and a cache folder;
it reads no environment variable. Thread count is not the cause: one core and two cores give
the same digest. Pinning kernels would mean patching stressonnx, which we do not do. The rule is
therefore D-021: exact on one machine, under 0.1% across processors, checked by CI.

The CR LF finding above is fixed: `tonika annotate` keeps every line ending, from a file or
standard input to `-o` or standard output. The trial text converted to CR LF goes through the
command line and comes back byte for byte once the marks are undone.

## 2026-11-16 · The HTTP API on a long request · pull request #7

`POST /v1/annotate` with the first 20,000 code points of the trial text (the API's limit),
`target` `plus`, timed with `curl` against `tonika serve` in the Codespace: 2 cores (AMD EPYC
7763, x86-64-v3), 8 GB, Python 3.13.18, `stressonnx-0.0.2:ruaccent@b8ba7afd`, model files
already in the local cache.

| Request | Time |
| --- | --- |
| First after start (includes loading the model) | 41.4 s |
| Second | 39.8 s |
| Third | 39.4 s |
| A 30-character sentence afterwards | 0.2 s |

The three answers were identical. Loading the model from the cache costs about 2 s; on a new
machine the first request also waits for the download of about 480 MB. `/v1/languages` answered
in 14 ms without loading anything.

What it means: about 500 characters per second on this machine, so a 20,000-character request
keeps a client waiting some 40 seconds, and a 30-minute text (31,000 characters) takes about a
minute in all. The editor (2.3) should send paragraphs of about 2,000 characters, which come
back in about 4 seconds each and show progress. Hosting (2.5) needs a model kept in memory
(about 700 MiB) and is CPU-bound: with `TONIKA_PARALLEL=1` a long request holds the model
until it is done, and the next one waits.
