"""Hybrid retrieval: dense (embeddings) + sparse (BM25), fused with Reciprocal Rank Fusion.

Why hybrid: dense search finds paraphrases ("termination" for "ending the contract"), BM25 finds exact tokens that
embeddings blur (clause numbers, product codes, names, figures). RRF combines the two rankings without having to
calibrate their very different score scales. evals/ measures each mode separately on the same questions.

Why no vector database: each query searches the chunks of the selected documents only (hundreds to a few thousand
vectors). A NumPy dot product over that is a few milliseconds, so FAISS or a hosted vector DB would add moving parts
without a measurable gain at this scale. The Retriever interface keeps that swap open.
"""

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from app.retrieval.embeddings import Embedder

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
STOPWORDS = frozenset(
    "a an the and or but if of to in on at by for with from as is are was were be been being it its this that these those "
    "what which who whom whose when where why how do does did can could should would will may might must shall i you he she "
    "we they me him her us them my your our their not no yes so than then there here about into over under after before".split()
)


# BM25's vote counts this much relative to the dense ranking. Chosen with evals/run_retrieval.py (see results/).
SPARSE_WEIGHT = 1.0


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Candidate:
    id: str
    document_id: str
    text: str
    page_start: int
    page_end: int
    heading: str | None
    embedding: np.ndarray | None


@dataclass
class Hit:
    candidate: Candidate
    score: float
    dense_rank: int | None
    sparse_rank: int | None


def rrf(rankings: list[list[str]], k: int = 60, weights: list[float] | None = None) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking, w in zip(rankings, weights or [1.0] * len(rankings), strict=True):
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + w / (k + rank + 1)
    return scores


def search(
    candidates: list[Candidate], query: str, embedder: Embedder, k: int = 6, mode: str = "hybrid", sparse_weight: float = SPARSE_WEIGHT
) -> list[Hit]:
    if not candidates or not query.strip():
        return []
    by_id = {c.id: c for c in candidates}
    dense: list[str] = []
    sparse: list[str] = []

    if mode in ("hybrid", "dense"):
        usable = [c for c in candidates if c.embedding is not None]
        if usable:
            matrix = np.stack([c.embedding for c in usable])
            sims = matrix @ embedder.embed_query(query)
            dense = [usable[i].id for i in np.argsort(-sims)[: max(k * 4, 20)]]

    if mode in ("hybrid", "sparse"):
        q = tokenize(query)
        if q:
            bm25 = BM25Okapi([tokenize((c.heading or "") + " " + c.text) or ["_"] for c in candidates])
            scores = bm25.get_scores(q)
            order = [i for i in np.argsort(-scores) if scores[i] > 0][: max(k * 4, 20)]
            sparse = [candidates[i].id for i in order]

    pairs = [(r, w) for r, w in ((dense, 1.0), (sparse, sparse_weight)) if r]
    fused = rrf([r for r, _ in pairs], weights=[w for _, w in pairs])
    dense_pos = {cid: i + 1 for i, cid in enumerate(dense)}
    sparse_pos = {cid: i + 1 for i, cid in enumerate(sparse)}
    ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
    return [Hit(by_id[cid], score, dense_pos.get(cid), sparse_pos.get(cid)) for cid, score in ranked]
