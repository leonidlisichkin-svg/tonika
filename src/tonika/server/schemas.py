"""Request and response bodies of API v1."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tonika.packs import Tier


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class AnnotateRequest(_Strict):
    text: str = Field(description="0 to TONIKA_MAX_CHARS code points after NFC")
    lang: str = Field("ru", description="Language tag")
    target: str = Field("acute", description="A notation or an engine preset id")
    mode: str | None = Field(
        None, description="ambiguous, all or yo; by default what the language pack supports"
    )
    dictionary: str | None = Field(
        None, description="A user dictionary in the format of docs/DICTIONARY.md"
    )
    document: bool = Field(False, description="Also return the Intent Document")


class AnnotateResponse(BaseModel):
    text: str
    lang: str
    target: str
    notation: str
    mode: str
    model: str
    tier: Tier
    demo: bool
    tonika: str
    document: dict[str, Any] | None = None


class EngineInfo(BaseModel):
    id: str
    name: str
    notation: str
    languages: list[str]
    verified_by: str
    verified_on: str
    source_url: str
    notes: str


class EnginesResponse(BaseModel):
    notations: list[str]
    modes: list[str]
    engines: list[EngineInfo]


class LanguageInfo(BaseModel):
    lang: str
    tier: Tier
    model: str
    demo: bool
    default_mode: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]


class HealthResponse(BaseModel):
    status: str
    tonika: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
