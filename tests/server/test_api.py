"""The acceptance tests of docs/specs/api-v1.md, offline with the demo pack."""

from __future__ import annotations

import gzip
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

import jsonschema
from fastapi.testclient import TestClient

from helpers import FakeStressonnx
from tonika import IntentDocument, __version__, annotate
from tonika.engines import list_engines
from tonika.packs import PackError
from tonika.render import MODES, NOTATIONS
from tonika.server import Settings, create_app

ROOT = Path(__file__).parents[2]
SCHEMA = json.loads((ROOT / "spec" / "intent-document.schema.json").read_text(encoding="utf-8"))
TRIAL = ROOT / "data" / "trials" / "ru" / "chekhov-lady-with-the-dog.txt"
PROOF = "В старом замке сломался замок. Все еще тут."


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TONIKA_PACK", "fake")
    for name in ("TONIKA_MAX_CHARS", "TONIKA_PARALLEL", "TONIKA_CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    return TestClient(create_app())


def _post(client: TestClient, **body: Any) -> Any:
    return client.post("/v1/annotate", json=body)


# 1. The same text as the library ---------------------------------------------------------------


@pytest.mark.parametrize("target", [*NOTATIONS, "yandex-speechkit"])
@pytest.mark.parametrize("mode", [None, *MODES])
def test_text_equals_the_library(client: TestClient, target: str, mode: str | None) -> None:
    body: dict[str, Any] = {"text": PROOF, "target": target}
    if mode is not None:
        body["mode"] = mode
    response = _post(client, **body)
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == annotate(PROOF, target=target, mode=mode, pack="fake")
    assert data["target"] == target
    assert data["mode"] == (mode or "ambiguous")
    assert data["notation"] == ("plus" if target == "yandex-speechkit" else target)


def test_a_dictionary_is_applied_as_in_the_library(client: TestClient) -> None:
    from tonika import UserDictionary

    dictionary = "+Окленд\nз+амок\n"
    text = "Замок в Окленде и замок."
    data = _post(client, text=text, target="plus", dictionary=dictionary).json()
    expected = annotate(
        text, target="plus", pack="fake", dictionary=UserDictionary.parse(dictionary)
    )
    assert data["text"] == expected


def test_the_trial_text_comes_out_as_from_the_library(client: TestClient) -> None:
    text = TRIAL.read_text(encoding="utf-8")[:20_000]
    for notation in NOTATIONS:
        for mode in MODES:
            data = _post(client, text=text, target=notation, mode=mode).json()
            assert data["text"] == annotate(text, target=notation, mode=mode, pack="fake"), (
                notation,
                mode,
            )


# 2. The Intent Document ---------------------------------------------------------------------


def test_the_document_is_returned_only_when_asked(client: TestClient) -> None:
    with_document = _post(client, text=PROOF, document=True).json()
    document = IntentDocument.from_dict(with_document["document"])
    jsonschema.validate(with_document["document"], SCHEMA)
    assert document.text == PROOF
    assert "document" not in _post(client, text=PROOF).json()
    # The document does not depend on the target or the mode.
    other = _post(client, text=PROOF, target="upper", mode="all", document=True).json()
    assert other["document"] == with_document["document"]


# 3. The demo pack says so ---------------------------------------------------------------------


def test_demo_is_true_with_the_demo_pack(client: TestClient) -> None:
    data = _post(client, text=PROOF).json()
    assert data["demo"] is True
    assert data["model"] == "fake-0"
    assert data["tier"] == "A"
    assert data["tonika"] == __version__


# 4. Every error row ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"text": PROOF, "lang": "xx"}, 400, "unknown_language"),
        ({"text": PROOF, "target": "foo"}, 400, "unknown_target"),
        ({"text": PROOF, "mode": "loud"}, 400, "unknown_mode"),
        ({"text": PROOF, "dictionary": "+Окленд\nэто = \n"}, 400, "dictionary_error"),
        ({"text": "а" * 20_001}, 413, "text_too_long"),
        ({"text": PROOF, "dictionary": "+а\n" * 7_000}, 413, "text_too_long"),
        ({}, 422, "invalid_request"),
        ({"text": 5}, 422, "invalid_request"),
        ({"text": PROOF, "document": "yes"}, 422, "invalid_request"),
        ({"text": PROOF, "taget": "plus"}, 422, "invalid_request"),
    ],
)
def test_errors_have_the_spec_body(
    client: TestClient, body: dict[str, Any], status: int, code: str
) -> None:
    response = client.post("/v1/annotate", json=body)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["message"]


def test_the_unknown_target_message_points_to_the_engines(client: TestClient) -> None:
    message = _post(client, text=PROOF, target="foo").json()["error"]["message"]
    assert message == (
        "unknown target 'foo'; choose a notation (acute, plus, upper, yo) or an engine from "
        "/v1/engines"
    )


def test_a_dictionary_error_names_the_line(client: TestClient) -> None:
    message = _post(client, text=PROOF, dictionary="+Окленд\nэто = \n").json()["error"]["message"]
    assert "2" in message


def test_a_body_that_is_not_json(client: TestClient) -> None:
    response = client.post(
        "/v1/annotate", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_a_validation_error_does_not_echo_the_input(client: TestClient) -> None:
    secret = "секретный текст пользователя"
    response = _post(client, text=secret, document=secret)
    assert response.status_code == 422
    assert secret not in response.text
    assert "document" in response.json()["error"]["message"]


def test_a_pack_that_cannot_load_gives_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise PackError("no network")

    monkeypatch.setattr("tonika.server.app.analyze_with", fail)
    response = _post(client, text=PROOF)
    assert (response.status_code, response.json()["error"]["code"]) == (503, "pack_unavailable")


def test_anything_else_gives_a_generic_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(pack: object, text: str, *args: object) -> None:
        raise RuntimeError(f"broke on {text}")

    monkeypatch.setattr("tonika.server.app.analyze_with", fail)
    with caplog.at_level(logging.INFO, logger="tonika.server"):
        response = _post(client, text="тайный текст")
    assert (response.status_code, response.json()["error"]["code"]) == (500, "internal")
    assert "тайный" not in response.text
    assert "тайный" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_unknown_routes_have_the_spec_body(client: TestClient) -> None:
    response = client.get("/v1/nothing")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")


# 5. The limit, in code points after NFC ----------------------------------------------------------


def test_a_text_of_exactly_the_limit_passes(client: TestClient) -> None:
    assert _post(client, text="а" * 20_000).status_code == 200
    assert _post(client, text="а" * 20_001).status_code == 413


def test_the_limit_counts_code_points_after_nfc() -> None:
    app = create_app(Settings(pack="fake", max_chars=10))
    client = TestClient(app)
    decomposed = "ё" * 10  # 20 code points as sent, 10 after NFC
    assert client.post("/v1/annotate", json={"text": decomposed}).status_code == 200
    assert client.post("/v1/annotate", json={"text": "ё" * 11}).status_code == 413
    # Cyrillic is two bytes a letter in UTF-8: bytes do not count.
    assert client.post("/v1/annotate", json={"text": "ж" * 10}).status_code == 200


# 6. No text in the log ------------------------------------------------------------------------


def test_the_log_holds_no_text(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    secret = "Ни одно слово этого предложения не должно попасть в журнал."
    with caplog.at_level(logging.DEBUG):
        assert _post(client, text=secret, dictionary="+Окленд").status_code == 200
        assert _post(client, text=secret, target="nope").status_code == 400
    assert caplog.records, "the request was not logged at all"
    for word in ("предложения", "журнал", "Окленд"):
        assert word not in caplog.text
    assert f"chars={len(secret)}" in caplog.text
    assert "lang=ru" in caplog.text


# 7. Engines, languages, health -----------------------------------------------------------------


def test_engines_equal_the_library(client: TestClient) -> None:
    data = client.get("/v1/engines").json()
    assert data["notations"] == list(NOTATIONS)
    assert data["modes"] == list(MODES)
    assert [engine["id"] for engine in data["engines"]] == [e.id for e in list_engines()]
    first, engine = data["engines"][0], list_engines()[0]
    assert first == {
        "id": engine.id,
        "name": engine.name,
        "notation": engine.notation,
        "languages": list(engine.languages),
        "verified_by": engine.verified_by,
        "verified_on": engine.verified_on,
        "source_url": engine.source_url,
        "notes": engine.notes,
    }


def test_languages_and_health(client: TestClient) -> None:
    languages = client.get("/v1/languages").json()["languages"]
    assert {
        "lang": "ru",
        "tier": "A",
        "model": "fake-0",
        "demo": True,
        "default_mode": "ambiguous",
    } in languages
    assert client.get("/healthz").json() == {"status": "ok", "tonika": __version__}


def test_metadata_never_loads_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeStressonnx(monkeypatch)
    monkeypatch.setattr("tonika.packs._stressonnx_languages", lambda: frozenset({"ru", "uk"}))
    monkeypatch.setattr("tonika.packs._INSTANCES", {})
    client = TestClient(create_app(Settings(pack="auto")))
    languages = {entry["lang"]: entry for entry in client.get("/v1/languages").json()["languages"]}
    assert languages["ru"] == {
        "lang": "ru",
        "tier": "A",
        "model": "stressonnx-0.0.2:ruaccent@b8ba7afd",
        "demo": False,
        "default_mode": "ambiguous",
    }
    assert languages["uk"]["tier"] == "B"
    assert client.get("/healthz").status_code == 200
    assert fake.loads == 0


def test_concurrent_requests_load_the_model_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeStressonnx(monkeypatch, delay=0.05)
    monkeypatch.setattr("tonika.packs._stressonnx_languages", lambda: frozenset({"ru"}))
    monkeypatch.setattr("tonika.packs._INSTANCES", {})
    client = TestClient(create_app(Settings(pack="auto", parallel=4)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: _post(client, text="Замок.").status_code, range(16)))
    assert statuses == [200] * 16
    assert fake.loads == 1


# 8. The OpenAPI document --------------------------------------------------------------------


def test_openapi_lists_the_four_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/v1/annotate", "/v1/engines", "/v1/languages", "/healthz"}


# Privacy and transport -------------------------------------------------------------------------


def test_every_response_is_no_store(client: TestClient) -> None:
    for response in (
        _post(client, text=PROOF),
        _post(client, text=PROOF, target="foo"),
        client.get("/v1/engines"),
        client.get("/healthz"),
        client.get("/"),
    ):
        assert response.headers["cache-control"] == "no-store"
        assert "set-cookie" not in response.headers


def test_responses_are_gzipped_when_accepted(client: TestClient) -> None:
    text = TRIAL.read_text(encoding="utf-8")[:5_000]
    response = client.post("/v1/annotate", json={"text": text}, headers={"accept-encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["text"]  # the client decompressed it
    raw = client.post("/v1/annotate", json={"text": text}, headers={"accept-encoding": "identity"})
    assert "content-encoding" not in raw.headers
    assert gzip.compress(raw.content)  # sanity: the plain body is there


def test_cors_only_for_configured_origins() -> None:
    client = TestClient(create_app(Settings(pack="fake", cors_origins=("https://editor.example",))))
    allowed = client.get("/healthz", headers={"origin": "https://editor.example"})
    assert allowed.headers["access-control-allow-origin"] == "https://editor.example"
    other = client.get("/healthz", headers={"origin": "https://elsewhere.example"})
    assert "access-control-allow-origin" not in other.headers


def test_root_points_to_the_docs(client: TestClient) -> None:
    assert client.get("/").json()["docs"] == "/docs"


@pytest.mark.parametrize(
    ("environ", "message"),
    [
        ({"TONIKA_MAX_CHARS": "lots"}, "TONIKA_MAX_CHARS"),
        ({"TONIKA_PARALLEL": "0"}, "TONIKA_PARALLEL"),
    ],
)
def test_bad_settings_stop_the_start(environ: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_env(environ)


def test_settings_from_the_environment() -> None:
    settings = Settings.from_env(
        {
            "TONIKA_PACK": "fake",
            "TONIKA_MAX_CHARS": "500",
            "TONIKA_PARALLEL": "2",
            "TONIKA_CORS_ORIGINS": "https://a.example, https://b.example",
        }
    )
    assert settings == Settings("fake", 500, 2, ("https://a.example", "https://b.example"))
