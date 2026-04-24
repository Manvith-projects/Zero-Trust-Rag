from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    auth0_domain: str = Field(..., alias="AUTH0_DOMAIN")
    auth0_audience: str = Field(..., alias="AUTH0_AUDIENCE")
    auth0_role_claim: str = Field("https://mycorp.example/roles", alias="AUTH0_ROLE_CLAIM")
    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field("zero_trust_rag", alias="QDRANT_COLLECTION")
    embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    llm_provider: str = Field("openai", alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    huggingface_api_token: str | None = Field(default=None, alias="HUGGINGFACE_API_TOKEN")
    huggingface_model: str = Field(
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        alias="HUGGINGFACE_MODEL",
    )
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )
    request_timeout_seconds: float = Field(30.0, alias="REQUEST_TIMEOUT_SECONDS")

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
