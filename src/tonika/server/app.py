"""Routes of API v1. Every answer is what the library gives for the same input and model."""

from __future__ import annotations

import logging
import threading
import time
import warnings
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from tonika import __version__
from tonika.dictionary import DictionaryError, UserDictionary
from tonika.engines import UnknownEngineError, list_engines, resolve_target
from tonika.packs import (
    DemoPackWarning,
    LanguagePack,
    PackError,
    UnknownPackError,
    available_packs,
    get_pack,
)
from tonika.pipeline import analyze_with, default_mode
from tonika.render import MODES, NOTATIONS, render
from tonika.server.schemas import (
    AnnotateRequest,
    AnnotateResponse,
    EngineInfo,
    EnginesResponse,
    ErrorResponse,
    HealthResponse,
    LanguageInfo,
    LanguagesResponse,
)
from tonika.server.settings import Settings
from tonika.text import normalize

logger = logging.getLogger("tonika.server")

STATIC = Path(__file__).parent / "static"

_ERRORS: dict[int | str, dict[str, object]] = {
    400: {
        "model": ErrorResponse,
        "description": "Unknown language, target or mode, or a bad dictionary",
    },
    413: {"model": ErrorResponse, "description": "Text or dictionary over the limit"},
    422: {"model": ErrorResponse, "description": "The body is not the object described"},
    503: {"model": ErrorResponse, "description": "The language pack could not load its models"},
}


class ApiError(Exception):
    """An error with the spec's body: ``{"error": {"code": ..., "message": ...}}``."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API. ``settings`` default to :meth:`Settings.from_env`."""
    settings = Settings.from_env() if settings is None else settings
    gate = threading.BoundedSemaphore(settings.parallel)
    app = FastAPI(
        title="Tonika",
        version=__version__,
        description="Open pronunciation layer for any TTS engine. Contract: docs/specs/api-v1.md.",
    )
    app.state.settings = settings
    _warn_about_demo_pack(settings)

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's own 422 body echoes the input; this one names only the fields at fault.
        return _error(422, "invalid_request", _describe_validation(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed"}
        return _error(exc.status_code, codes.get(exc.status_code, "http_error"), str(exc.detail))

    @app.middleware("http")
    async def _log_and_no_store(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        state = request.scope.get("state", {})
        # Route, status, time, text length and language: never the text.
        logger.info(
            "%s %s %d %.0f ms chars=%s lang=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            state.get("chars", "-"),
            state.get("lang", "-"),
        )
        return response

    @app.post(
        "/v1/annotate",
        response_model=AnnotateResponse,
        response_model_exclude_unset=True,
        responses=_ERRORS,
    )
    def annotate(body: AnnotateRequest, request: Request) -> AnnotateResponse:
        """Mark pronunciation in ``text``: what ``tonika.annotate`` returns, byte for byte."""
        text = normalize(body.text)
        request.scope.setdefault("state", {}).update(chars=len(text), lang=body.lang)
        if len(text) > settings.max_chars:
            raise ApiError(
                413,
                "text_too_long",
                f"the text has {len(text):,} characters; the limit is {settings.max_chars:,}. "
                "Split it at paragraph breaks and send the parts one after another.",
            )
        notation = _notation(body.target)
        if body.mode is not None and body.mode not in MODES:
            raise ApiError(
                400, "unknown_mode", f"unknown mode {body.mode!r}; choose from {', '.join(MODES)}"
            )
        dictionary = _dictionary(body.dictionary, settings.max_chars)
        with gate:
            pack = _pack(body.lang, settings.pack)
            try:
                document = analyze_with(pack, text, dictionary)
            except PackError as exc:
                logger.warning("the %r pack could not run: %s", body.lang, type(exc).__name__)
                raise ApiError(
                    503,
                    "pack_unavailable",
                    f"the language pack for {body.lang!r} could not load its models; "
                    "try again later",
                ) from None
            except Exception as exc:
                # The message of an unexpected error may quote the text: log only its type.
                logger.error("annotate failed: %s", type(exc).__name__)
                raise ApiError(500, "internal", "something went wrong on the server") from None
        mode = body.mode or default_mode(pack)
        response = AnnotateResponse(
            text=render(document, notation, mode),
            lang=pack.lang,
            target=body.target,
            notation=notation,
            mode=mode,
            model=document.model,
            tier=pack.tier,
            demo=pack.demo,
            tonika=__version__,
        )
        if body.document:
            response.document = document.to_dict()
        return response

    @app.get("/v1/engines", response_model=EnginesResponse)
    def engines() -> EnginesResponse:
        """The engine presets a ``target`` may name, and the notations and modes."""
        return EnginesResponse(
            notations=list(NOTATIONS),
            modes=list(MODES),
            engines=[
                EngineInfo(
                    id=engine.id,
                    name=engine.name,
                    notation=engine.notation,
                    languages=list(engine.languages),
                    verified_by=engine.verified_by,
                    verified_on=engine.verified_on,
                    source_url=engine.source_url,
                    notes=engine.notes,
                )
                for engine in list_engines()
            ],
        )

    @app.get("/v1/languages", response_model=LanguagesResponse)
    def languages() -> LanguagesResponse:
        """The languages this server can annotate. Answering never loads a model."""
        entries: list[LanguageInfo] = []
        for lang in available_packs():
            try:
                pack = _quiet_pack(lang, settings.pack)
            except UnknownPackError:
                continue
            entries.append(
                LanguageInfo(
                    lang=lang,
                    tier=pack.tier,
                    model=pack.model,
                    demo=pack.demo,
                    default_mode=default_mode(pack),
                )
            )
        return LanguagesResponse(languages=entries)

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        """Always ``ok`` while the server runs. Does not touch the models."""
        return HealthResponse(status="ok", tonika=__version__)

    if (STATIC / "index.html").is_file():
        app.mount("/", StaticFiles(directory=STATIC, html=True), name="editor")
    else:

        @app.get("/", include_in_schema=False)
        def root() -> dict[str, str]:
            return {"name": "Tonika HTTP API", "tonika": __version__, "docs": "/docs"}

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["content-type"],
        )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers={"Cache-Control": "no-store"},
    )


def _notation(target: str) -> str:
    try:
        return resolve_target(target)
    except UnknownEngineError:
        raise ApiError(
            400,
            "unknown_target",
            f"unknown target {target!r}; choose a notation ({', '.join(NOTATIONS)}) "
            "or an engine from /v1/engines",
        ) from None


def _dictionary(text: str | None, limit: int) -> UserDictionary | None:
    if text is None:
        return None
    text = normalize(text)
    if len(text) > limit:
        raise ApiError(
            413,
            "text_too_long",
            f"the dictionary has {len(text):,} characters; the limit is {limit:,}",
        )
    try:
        return UserDictionary.parse(text, source="dictionary")
    except DictionaryError as exc:
        raise ApiError(400, "dictionary_error", str(exc)) from None


def _pack(lang: str, name: str) -> LanguagePack:
    try:
        return _quiet_pack(lang, name)
    except UnknownPackError:
        raise ApiError(
            400, "unknown_language", f"no language pack for {lang!r}; see /v1/languages"
        ) from None


def _quiet_pack(lang: str, name: str) -> LanguagePack:
    """Get a pack without a demo-pack warning per request; the server warns once at start."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DemoPackWarning)
        return get_pack(lang, name)


def _warn_about_demo_pack(settings: Settings) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DemoPackWarning)
        for lang in available_packs():
            try:
                get_pack(lang, settings.pack)
            except UnknownPackError:
                continue
    for warning in caught:
        if issubclass(warning.category, DemoPackWarning):
            logger.warning("%s", warning.message)


def _describe_validation(exc: RequestValidationError) -> str:
    problems: list[str] = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error.get("loc", ()) if part != "body") or "body"
        kind = str(error.get("type", "invalid"))
        reason = {
            "missing": "is required",
            "extra_forbidden": "is not a known field",
            "string_type": "must be a string",
            "bool_type": "must be true or false",
            "json_invalid": "is not valid JSON",
            "model_attributes_type": "must be a JSON object",
            "dict_type": "must be a JSON object",
        }.get(kind, "is invalid")
        problems.append(f"{where} {reason}")
    return (
        "the body must be a JSON object with a string 'text' and optional 'lang', 'target', "
        "'mode', 'dictionary' and 'document': " + "; ".join(problems)
    )
