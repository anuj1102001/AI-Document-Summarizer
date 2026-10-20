"""Process-wide singletons, exposed as FastAPI dependencies so tests can swap them."""

from functools import lru_cache

from app.config import Settings, get_settings
from app.db import Database
from app.llm.client import LLM, build_llm
from app.retrieval.embeddings import Embedder, build_embedder


def get_settings_dep() -> Settings:
    return get_settings()


@lru_cache
def _db() -> Database:
    return Database(get_settings().db_path)


def get_db() -> Database:
    return _db()


@lru_cache
def _embedder() -> Embedder:
    s = get_settings()
    return build_embedder(s.embedding_backend, s.embedding_model)


def get_embedder() -> Embedder:
    return _embedder()


@lru_cache
def _llm() -> LLM:
    return build_llm(get_settings())


def get_llm() -> LLM:
    return _llm()
