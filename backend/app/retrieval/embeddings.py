"""Text embeddings.

Production uses BAAI/bge-small-en-v1.5 through fastembed (ONNX, CPU, ~130 MB RAM, no API key, no per-call cost).
Tests and offline demos use a deterministic hashing embedder so they run in milliseconds with no downloads.
"""

import hashlib
import re
from typing import Protocol

import numpy as np

# bge models are trained with this instruction prefix for queries (not for passages).
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    name: str
    dim: int

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    return (m / np.maximum(norms, 1e-12)).astype(np.float32)


class FastEmbedder:
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.name = model_name
        self._model = TextEmbedding(model_name)
        self.dim = len(next(iter(self._model.embed(["dimension probe"]))))
        self._query_prefix = BGE_QUERY_PREFIX if "bge" in model_name.lower() else ""

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return _normalize(np.array(list(self._model.embed(texts, batch_size=64))))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(np.array(list(self._model.embed([self._query_prefix + text]))[0]))


_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    """Bag-of-words hashed into a fixed vector. Captures word overlap only; good enough to test the plumbing."""

    def __init__(self, dim: int = 512):
        self.name = f"hashing-{dim}"
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in _TOKEN.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        return v

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return _normalize(np.stack([self._vec(t) for t in texts]))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(self._vec(text))


def build_embedder(backend: str, model_name: str) -> Embedder:
    if backend == "hashing":
        return HashingEmbedder()
    return FastEmbedder(model_name)
