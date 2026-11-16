# Web editor

Status: specification for roadmap items 2.2 to 2.4. Changing it needs a `DECISIONS.md` entry.

One screen, made for a phone held in one hand. An author pastes a script, looks only at the words
Tonika is unsure about, and copies text ready for the TTS engine. A 30-minute script should take a
few minutes of attention.

## Principles

1. **One screen, three states**: empty, working, ready. No navigation, no accounts.
2. **Attention goes to doubt.** Everything Tonika is sure of stays quiet. Doubtful words are the
   only accent on the page.
3. **What you see is what you copy.** The result shows the exact text the engine will receive.
4. **The server analyses, the browser renders.** After analysis every interaction is instant and
   needs no request: changing engine, mode or a reading.
5. **Nothing leaves without consent.** Text goes to the same-origin API for analysis and nowhere
   else. Nothing is sent to the open dataset in this phase.

## Stack

- `web/`: Vite, React, TypeScript in strict mode. Runtime dependencies: `react`, `react-dom`, and
  nothing else. No UI kit, no state library, no CSS framework, no web fonts.
- Dev dependencies: `vite`, `@vitejs/plugin-react`, `typescript`, `vitest`, `jsdom`, `prettier`.
  Anything more needs Leo's yes.
- Styles: plain CSS with custom properties in `web/src/styles/`.
- `npm run build` writes to `src/tonika/server/static/` (ignored by git); the API serves it at `/`.
- `npm run dev` proxies `/v1` to `http://127.0.0.1:8000`.
- CI job `web`: `npm ci`, `npm run check` (`tsc --noEmit` and `prettier --check`), `npm test`,
  `npm run build`.

## The browser renders: TypeScript port and conformance vectors

`web/src/core/` holds pure functions with no React in them:

| Function | Mirrors |
| --- | --- |
| `render(document, notation, mode): string` | `tonika.render.render` |
| `markStress(word, indices, notation): string` | `tonika.render.mark_stress` |
| `choose(token, alternativeIndex): Token` | see "Choosing a reading" |
| `splitBlocks(text, limit): string[]` and `joinBlocks` | see "Blocks" |

All offsets are **code points**, not UTF-16 units: work on `Array.from(text)`.

`spec/render-vectors.json` (CC0) keeps the two implementations identical. It is a list of cases:

```json
{"name": "ambiguous token, plus", "document": {…}, "notation": "plus", "mode": "ambiguous", "expected": "В старом з+амке сломался зам+ок."}
```

- A Python test builds the cases from documents covering every branch of `render` (each notation
  and mode; ambiguous and plain tokens; `respell`; sources `input` and `user`; no stress; text
  before, between and after tokens; an astral-plane character before a token) and fails when the
  committed file differs from what it builds.
- A vitest test runs every case through the TypeScript `render`.
- Engine ids resolve to notations through `/v1/engines`; `render` takes notations only.

## Blocks

A long text is analysed in blocks so that results appear progressively and an edit re-analyses
only what changed.

- `splitBlocks` cuts at line breaks and packs whole lines into blocks of at most 2 000 code
  points. Line breaks stay inside the blocks, so `joinBlocks(splitBlocks(t)) === t` always.
  A single line over the limit is cut at the last sentence end before the limit, else at the last
  space, else hard.
- Blocks are sent one at a time, in order, as `POST /v1/annotate` with `"document": true`.
- A block's key is a hash of its text, the dictionary and the language. Results are kept by key
  in memory, so editing the text re-analyses only blocks whose key is new.
- The final text is the blocks rendered in order and joined.

```ts
type Block = {
  key: string;
  text: string;
  status: "waiting" | "working" | "ready" | "failed";
  document?: IntentDocument;
  choices: Record<number, number>; // token index → index into that token's alternatives
  error?: string;
};
```

## Choosing a reading

`choose(token, j)` returns the token with `reading = alternatives[j]`,
`alternatives = [old reading, …the others]` and `source = "user"`. Sources `user` and `input` are
marked in every mode, exactly as in Python. Undo removes the choice; the original document is
never mutated.

"Everywhere in this text" applies the same choice to every token with the same form (compared in
lower case, ё as е) that offers the same reading. It is local to the open text.

## The screen

Russian is the first interface language; English is the second. All strings live in one file.

**Empty.** Wordmark. One large field: «Вставьте текст». Under it a quiet line of controls and one
primary button, «Расставить ударения».

**Controls**, visible in every state:

- Engine: «Яндекс SpeechKit», «Silero», «Акут (а́)», «Заглавная (А)», from `/v1/engines`.
  The choice says in one line what the engine will receive: «Плюс перед ударной: з+амок».
- What to mark: «Спорные слова» / «Все слова» / «Только ё».
- «Мой словарь»: opens a sheet with a text field in the dictionary format and three example lines.
  A bad line shows the server's message under the field.

**Working.** The result appears block by block. A thin line of progress and «Абзацы: 3 из 14».
The author can start reading and choosing at once. A failed block shows «Не получилось.
Повторить» in place and does not stop the others.

**Ready.** The text flows as paragraphs. A doubtful word (a token with alternatives) carries a
dotted underline in the accent colour; once the author has chosen or confirmed it, the underline
becomes solid and quiet. Stressed letters are tinted with the accent in every marked word.

- A sticky bar at the bottom: «Спорных слов: 12 · проверено 3», «Проверить», «Скопировать».
- **«Проверить»** walks through the doubtful words in order: scrolls to the word, opens the sheet.
  Choosing a reading, or «Оставить как есть», moves to the next. «3 из 12» and back / forward.
- **Tapping a word** opens the same sheet for that word.
- **The sheet** shows the sentence with the word highlighted and the readings as large buttons,
  each with its stressed letter tinted and an acute accent whatever the engine is (за́мок, замо́к).
  Below: «Так везде в этом тексте» and «Отменить».
- **«Скопировать»** copies the final text and answers «Скопировано · 27 412 знаков». Next to it,
  «Скачать .txt».
- When `demo` is true a quiet banner says: «Демо-режим: настоящая модель не подключена».

Kept between visits in `localStorage`: engine, mode, dictionary. Kept in `sessionStorage` until
the tab closes: the text and the choices. Wrap every storage call in `try`.

## Look

Calm, editorial, unhurried. The page is the author's text; the interface steps back.

| Token | Light | Dark |
| --- | --- | --- |
| `--paper` | `#FAF8F4` | `#141311` |
| `--ink` | `#1B1A17` | `#ECE7DD` |
| `--muted` | `#6F6A60` | `#9A9488` |
| `--line` | `#E5E0D6` | `#2A2824` |
| `--accent` | `#8A6A2F` | `#C9A566` |
| `--accent-soft` | `#F1E9DA` | `#2A241A` |

- One accent colour, used only for doubt, stress and the primary button. No gradients, no shadows
  heavier than a hairline, no icons where a word is clearer.
- Text: `Charter, "Noto Serif", Georgia, "Times New Roman", serif`, 18px, line height 1.6, measure
  up to 66 characters. Interface: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- Spacing on a 4px grid; generous margins; the text column is centred on wide screens.
- Motion: 160ms ease-out for the sheet and for underline changes; none under
  `prefers-reduced-motion`. Dark theme follows `prefers-color-scheme`.

## Quality bar

- **Phone first**: designed at 360px wide; works with one thumb; safe-area insets respected.
- **Fast**: JavaScript at most 120 KB gzipped; first paint without waiting for any request; a text
  of 30 000 characters with 4 000 tokens scrolls and responds without visible delay (tokens are
  spans, everything else plain text; render paragraphs lazily if needed).
- **Accessible**: every doubtful word is a button with a label like «замок, спорное слово, выбрано
  за́мок»; the sheet is a dialog that traps focus and closes on Escape; touch targets at least
  44px in the sheet and the bar; contrast at least 4.5:1; everything works from a keyboard.
- **Honest**: no fake progress; a failure says what failed and offers one action.

## Not in this phase

Accounts, saving texts on the server, sending corrections to the dataset (Phase 3), meanings of
readings (need the lexicon), listening to a word, languages other than Russian.
