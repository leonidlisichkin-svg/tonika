# The dataset loop

Status: specification for Phase 3. Roadmap item 3.1 implements the first half (records and
checks). The second half (collection, review, releases) needs decisions from Leo, marked **Ask**.

The loop: an author corrects or confirms a reading in the editor → the sentence becomes a public
example → the decision lists are rebuilt → the answer changes for everyone.

## 1. Records

One JSON object per line in `data/examples/<lang>/<lang>-NNNN.jsonl`, at most 5 000 lines a file,
in the format of `docs/DATA_SPEC.md` section 1, with two additions:

| Field | Type | Meaning |
| --- | --- | --- |
| `origin` | string | `correction` (the author changed the engine's reading), `confirmation` (the author kept it) or `editor` (written by a language editor) |
| `was` | object, optional | For a correction: the reading the engine had given |

Confirmations matter as much as corrections: rules are learnt by comparing readings, so the
dataset needs examples of both.

## 2. Checks: `tonika data check <path>`

Exit code 1 and one line per problem (`file:line: message`) when any record fails. All offline.

Each record:

1. Valid JSON object with exactly the known fields; `license` is `CC0-1.0`.
2. `text` is NFC, one sentence, 3 to 300 code points, no line break, no control characters.
3. `text[start:end] == form` (code points), and `form` is a single word of `text.iter_words`.
4. Every stress index points at a vowel of the surface form. A `respell` differs from `form`
   only in ways the language allows (Russian: е ↔ ё, case kept).
5. The sentence is written in the language's script: for `ru`, at least 80% of its letters are
   Cyrillic.
6. No personal data patterns: e-mail addresses, URLs, phone-like digit runs, `@handles`.
7. `id` matches `<lang>-<six digits>`.

The whole set:

8. Ids are unique and files are sorted by id.
9. No two records share `text`, `start` and `reading` (duplicates).
10. Records that share `text` and `start` but differ in `reading` are reported as **disputed**;
    both must carry `"status": "disputed"` to pass.
11. No example sentence appears in any golden set (compare folded text). The golden sets stay
    held out.

CI runs the check over `data/examples/` on every pull request.

## 3. Collection (**Ask** before building)

What the editor sends, and only when the author presses «Отправить исправления в открытый
словарь» after reading this text:

> Отправятся только отдельные предложения с исправленными или подтверждёнными словами, без
> остального текста. Они станут общедоступными и свободными для любого использования (CC0).
> Не отправляйте предложения с личными данными.

- One record per decided word: the single sentence that contains it (cut with
  `segment.iter_chunks`), never the whole text.
- `POST /v1/contributions` with a list of proposed records (no `id`, `status` or `votes`). The
  server runs checks 1 to 6 and answers how many were accepted into the queue.
- No account. To count independent confirmations the server keeps, per record, a set of
  one-way hashes of (client address + a secret that changes daily). The address itself is never
  stored.
- Abuse limits: at most 200 records a request and 2 000 a day per client hash.

**Ask Leo:** where the queue lives. Recommended: a separate public repository, `tonika-data`,
used as the database. The server appends proposals to `inbox/<date>.jsonl` there through the
GitHub API with a token kept in the hosting's secrets, in batches. No database to run, full
history, anyone can audit. The alternative is a managed database, which is a new service.

## 4. Review

- A scheduled GitHub Action runs daily: validates the inbox, merges duplicates (adding their
  hashes as votes), marks conflicts as disputed, and opens one pull request, "Examples
  YYYY-MM-DD", that moves reviewed-ready records into `data/examples/`.
- A proposal is ready with three independent confirmations **and** no conflict. Everything else
  waits in the inbox.
- A language editor (first: Leo, for Russian) reads the pull request and merges it. Until the
  project has more editors, nothing enters the dataset without that merge. Votes only decide what
  is shown to the editor first.
- Disputed norms (тво́рог / творо́г): both readings are recorded as correct with
  `"status": "disputed"`; they produce no rule.

## 5. Releases

- A data release is a git tag `data-YYYY.MM.N` plus `data/VERSION`. The release job rebuilds
  `data/models/<lang>.dl.json` (`docs/specs/decision-lists.md`), runs the golden-set gate, and
  attaches the files.
- Every Intent Document names the data release through its `model` string.
- Mirror to Hugging Face Datasets after the first release (**Ask**: a new account).

## Exit test for Phase 3

A reading the engine gets wrong is corrected in the editor, sent, merged by the editor the same
day, released, and the engine's answer for that sentence changes. Each step is visible in git.
