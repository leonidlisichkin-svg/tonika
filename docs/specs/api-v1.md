# HTTP API v1

Status: specification for roadmap item 2.1. Changing it needs a `DECISIONS.md` entry.

The API is a thin, stateless wrapper over `tonika.analyze` and `tonika.render`. It adds no
behaviour of its own: for the same input and model it returns exactly what the library returns.

## Shape

- Optional extra `api` (FastAPI and uvicorn). The core never imports it.
- Code in `src/tonika/server/`: `create_app() -> FastAPI`, routes, request and response models.
- Started with `tonika serve [--host 127.0.0.1] [--port 8000]`.
- All routes are under `/v1`. Changes inside v1 are additive only. The Intent Document carries
  its own version in `spec`.
- JSON in, JSON out, UTF-8. Responses are compressed (gzip) when the client accepts it.

## Privacy

- Request bodies are never written to disk and never logged. Logs hold the route, status, time
  taken, text length and language only.
- No cache in v1. Every response carries `Cache-Control: no-store`.
- No accounts and no cookies.

## `POST /v1/annotate`

Request:

```json
{
  "text": "Замок был старый, все знали.",
  "lang": "ru",
  "target": "yandex-speechkit",
  "mode": "ambiguous",
  "dictionary": "+Окленд\nВерещ+агин*",
  "document": true
}
```

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `text` | string | required | 0 to 20 000 code points after NFC |
| `lang` | string | `"ru"` | Language tag |
| `target` | string | `"acute"` | A notation or an engine preset id |
| `mode` | string | pack default | `ambiguous`, `all` or `yo`. Default: `tonika.pipeline.default_mode(pack)` |
| `dictionary` | string | none | A user dictionary in the format of `docs/DICTIONARY.md`, up to 20 000 code points |
| `document` | boolean | `false` | Also return the Intent Document |

Response `200`:

```json
{
  "text": "Зам+ок был старый, вс+ё знали.",
  "lang": "ru",
  "target": "yandex-speechkit",
  "notation": "plus",
  "mode": "ambiguous",
  "model": "stressonnx-0.0.2:ruaccent@b8ba7afd",
  "tier": "A",
  "demo": false,
  "tonika": "0.1.0",
  "document": {"spec": "1.0", "lang": "ru", "model": "…", "text": "…", "tokens": []}
}
```

- `text` equals `tonika.annotate(...)` for the same arguments, byte for byte.
- `document` is `IntentDocument.to_dict()` and is present only when requested. It does not depend
  on `target` or `mode`: a client can re-render it in any notation without another request.
- `demo` is `true` when the server answered with the demo pack. Clients must show that.
- `notation` is the notation the target resolved to.

Long texts: the limit keeps one request short (the Russian models read a few hundred characters
a second on one CPU core). A client splits a long text at paragraph breaks, sends the parts one
after another and joins the results. Parts are independent, so this changes nothing in the output.

## `GET /v1/engines`

```json
{
  "notations": ["acute", "plus", "upper", "yo"],
  "modes": ["ambiguous", "all", "yo"],
  "engines": [
    {
      "id": "yandex-speechkit",
      "name": "Yandex SpeechKit",
      "notation": "plus",
      "languages": ["ru"],
      "verified_by": "documentation",
      "verified_on": "2026-11-16",
      "source_url": "https://…",
      "notes": "…"
    }
  ]
}
```

The list is `tonika.engines.list_engines()`, in its order.

## `GET /v1/languages`

```json
{
  "languages": [
    {"lang": "ru", "tier": "A", "model": "stressonnx-0.0.2:ruaccent@b8ba7afd", "demo": false, "default_mode": "ambiguous"}
  ]
}
```

One entry per language of `tonika.packs.available_packs()`, describing the pack that `"auto"`
selects. Building this list must not download models: packs load lazily, and `model` may be
reported without loading them.

## `GET /healthz`

`200` with `{"status": "ok", "tonika": "0.1.0"}`. Does not touch the models.

## Errors

Every error has the same body and a matching HTTP status:

```json
{"error": {"code": "unknown_target", "message": "unknown target 'foo'; choose a notation (acute, plus, upper, yo) or an engine from /v1/engines"}}
```

| Status | `code` | When |
| --- | --- | --- |
| 400 | `unknown_language` | No pack for `lang` |
| 400 | `unknown_target` | `target` is neither a notation nor an engine id |
| 400 | `unknown_mode` | `mode` is not one of the three |
| 400 | `dictionary_error` | The dictionary has a bad line; the message names the line number |
| 413 | `text_too_long` | `text` or `dictionary` is over its limit |
| 422 | `invalid_request` | The body is not the JSON object described above |
| 503 | `pack_unavailable` | The pack could not load its models (for example, no network on first use) |
| 500 | `internal` | Anything else. The message is generic; details go to the log, without the text |

Messages are written for the person using a client: plain, specific, no stack traces.

## Server settings

Environment variables, read once at start:

| Variable | Default | Meaning |
| --- | --- | --- |
| `TONIKA_PACK` | `auto` | Pack name passed to `get_pack`. Clients cannot choose packs |
| `TONIKA_MAX_CHARS` | `20000` | Limit for `text` and for `dictionary` |
| `TONIKA_PARALLEL` | `1` | Analyses that may run at the same time; the rest wait |
| `TONIKA_CORS_ORIGINS` | empty | Comma-separated origins allowed to call the API from a browser |

Analysis is CPU-bound. Handlers are plain `def` functions (FastAPI runs them in a thread pool)
behind a semaphore of `TONIKA_PARALLEL`, so memory stays bounded and one slow request cannot
starve `/healthz`.

`GET /` serves the built web editor when it is present in `src/tonika/server/static/`; otherwise
it returns a short JSON pointer to `/docs`.

## Not in v1

Accounts, API keys, quotas, rate limits, batch jobs, streaming, storing text, team dictionaries.
Rate limiting for a public deployment is decided in roadmap item 2.5.

## Acceptance tests

Offline, with `TONIKA_PACK=fake`, using FastAPI's test client:

1. `POST /v1/annotate` returns the same `text` as `tonika.annotate` for each notation, each mode,
   one engine id, and with a dictionary.
2. With `"document": true` the document passes `IntentDocument.from_dict` and the JSON Schema in
   `spec/`; without it the key is absent.
3. `demo` is `true` with the demo pack.
4. Each error row above is produced by a test, with its status and code.
5. A text of exactly the limit passes; one code point more gives `413`.
6. The log of a request does not contain the text (capture the log in the test).
7. `/v1/engines` equals `list_engines()`; `/v1/languages` lists `ru`; `/healthz` is `200`.
8. `GET /openapi.json` lists the four routes.
