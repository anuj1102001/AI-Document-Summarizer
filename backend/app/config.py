"""Runtime configuration. Every value can be set with an environment variable (or a local .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM (generation only; retrieval runs locally and never needs a key)
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-3.5-flash"
    llm_timeout_s: float = 90.0
    llm_max_retries: int = 2

    # Embeddings: a small local model, so indexing is free, private and reproducible.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_backend: str = "fastembed"  # "fastembed" | "hashing" (tests and offline demos)

    # Storage
    data_dir: Path = Path("data")

    # Upload limits
    max_upload_mb: int = 20
    max_pages: int = 400

    # Chunking and retrieval
    chunk_chars: int = 1100
    chunk_overlap: int = 160
    retrieval_k: int = 6
    # Below this many characters a document is summarised in one call; above it, map-reduce over sections.
    single_pass_chars: int = 180_000

    # Abuse protection: LLM calls per workspace per hour.
    llm_calls_per_hour: int = 60

    # CORS: the frontend origin(s), comma separated.
    cors_origins: str = "http://localhost:3000"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "margin.db"

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
