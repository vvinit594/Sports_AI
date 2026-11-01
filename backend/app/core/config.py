"""Environment-driven application settings for the Phase 3 API."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CRICSHEET_DIR = REPO_ROOT / "data" / "raw" / "cricsheet" / "samples"
DEFAULT_MODEL_DIR = BACKEND_ROOT / "models" / "artifacts"


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class Settings(BaseSettings):
    """Runtime settings. Secrets stay server-side and are never returned by the API."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("PULSEIQ_ENVIRONMENT", "environment"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("PULSEIQ_LOG_LEVEL", "log_level"),
    )
    api_title: str = "PulseIQ API"
    api_version: str = "0.3.0"

    cricsheet_dir: Path = Field(
        default=DEFAULT_CRICSHEET_DIR,
        validation_alias=AliasChoices("PULSEIQ_CRICSHEET_DIR", "cricsheet_dir"),
    )
    model_dir: Path = Field(
        default=DEFAULT_MODEL_DIR,
        validation_alias=AliasChoices("PULSEIQ_MODEL_DIR", "model_dir"),
    )
    model_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("PULSEIQ_MODEL_PATH", "model_path"),
    )
    cors_origins: str = Field(
        default="",
        validation_alias=AliasChoices("PULSEIQ_CORS_ORIGINS", "cors_origins"),
    )
    max_request_bytes: int = Field(
        default=32_768,
        validation_alias=AliasChoices("PULSEIQ_MAX_REQUEST_BYTES", "max_request_bytes"),
    )

    llm_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices("LLM_PROVIDER", "llm_provider"),
    )
    llm_model: str = Field(
        default="mock-explanations-v1",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias=AliasChoices("GEMINI_BASE_URL", "gemini_base_url"),
    )
    llm_timeout_seconds: float = Field(
        default=20.0,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds"),
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias=AliasChoices("LLM_MAX_RETRIES", "llm_max_retries"),
    )

    @field_validator("gemini_api_key", "openai_api_key", "model_path", mode="before")
    @classmethod
    def _empty_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return _blank_to_none(value)
        return value

    @field_validator(
        "llm_provider", "llm_model", "environment", "log_level", mode="before"
    )
    @classmethod
    def _strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    def resolved_cricsheet_dir(self) -> Path:
        return _resolve_path(self.cricsheet_dir)

    def resolved_model_dir(self) -> Path:
        return _resolve_path(self.model_dir)

    def resolved_model_path(self) -> Path | None:
        if self.model_path is None:
            return None
        return _resolve_path(self.model_path)

    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    def normalized_llm_provider(self) -> str:
        return self.llm_provider.strip().lower()


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate
    backend_candidate = BACKEND_ROOT / path
    if backend_candidate.exists():
        return backend_candidate
    return (REPO_ROOT / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
