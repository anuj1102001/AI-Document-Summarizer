"""Retrieval evaluation. No API key needed; fully reproducible.

For every answerable question we know the page that contains the answer. A retrieval "hits" at k if any of the top-k
passages covers that page. We compare dense-only, BM25-only and hybrid (RRF) retrieval, scoped to the question's
document (how the app is used) and across the whole library (harder: other documents compete).

Run from backend/:  python -m evals.run_retrieval [--embedder fastembed|hashing]
"""

import argparse
import json
import platform
import statistics
import time
from datetime import date

from app.config import Settings
from app.retrieval.embeddings import build_embedder
from app.retrieval.search import search
from evals.common import RESULTS, build_corpus, load_questions

KS = (1, 3, 6)
MODES = ("dense", "sparse", "hybrid")
ABLATION_WEIGHTS = (1.0, 0.5, 0.3)


def first_hit_rank(hits, page: int) -> int | None:
    for i, h in enumerate(hits, start=1):
        if h.candidate.page_start <= page <= h.candidate.page_end:
            return i
    return None


def evaluate(corpus, questions, embedder, scope: str, modes=None) -> dict:
    all_chunks = [c for d in corpus.values() for c in d.chunks]
    table: dict[str, dict] = {}
    for mode in modes or [(m, 1.0) for m in MODES]:
        mode, weight = mode
        ranks, by_type, latencies = [], {}, []
        for q in questions:
            pool = corpus[q["doc"]].chunks if scope == "document" else all_chunks
            t = time.perf_counter()
            hits = search(pool, q["question"], embedder, k=max(KS), mode=mode, sparse_weight=weight)
            latencies.append((time.perf_counter() - t) * 1000)
            if scope == "library":
                # a passage from the wrong document never counts, even if its page number matches
                hits = [h if h.candidate.document_id == q["doc"] else _Miss() for h in hits]
            r = first_hit_rank(hits, q["page"])
            ranks.append(r)
            by_type.setdefault(q["type"], []).append(r)
        table[mode if weight == 1.0 else f"{mode} (sparse weight {weight})"] = {
            **{f"hit@{k}": _rate(ranks, k) for k in KS},
            "mrr@6": round(statistics.mean(1 / r if r else 0 for r in ranks), 3),
            **{f"{t}_hit@3": _rate(rs, 3) for t, rs in sorted(by_type.items())},
            "p50_ms": round(statistics.median(latencies), 2),
        }
    return table


class _Miss:
    """Stands in for a passage from the wrong document: it can never match the gold page."""

    def __init__(self):
        self.candidate = type("C", (), {"page_start": -1, "page_end": -1})()


def _rate(ranks: list[int | None], k: int) -> float:
    return round(sum(1 for r in ranks if r and r <= k) / len(ranks), 3)


def to_markdown(meta: dict, results: dict) -> str:
    lines = [
        "# Retrieval evaluation",
        "",
        f"Run on {meta['date']} · embedder `{meta['embedder']}` · chunks of {meta['chunk_chars']} chars with {meta['overlap']} overlap · "
        f"{meta['questions']} answerable questions over {meta['documents']} synthetic documents ({meta['pages']} pages, {meta['chunks']} chunks).",
        "",
        "A question counts as a hit at k if one of the top-k passages covers the page that holds the answer. "
        "MRR is the mean reciprocal rank of the first correct passage (0 if not in the top 6).",
        "",
    ]
    for scope, title in (("document", "Scoped to the question's document (how Ask works)"), ("library", "Across the whole library (four documents compete)")):
        rows = results[scope]
        cols = ["hit@1", "hit@3", "hit@6", "mrr@6", "exact_hit@3", "paraphrase_hit@3", "p50_ms"]
        lines += [f"## {title}", "", "| Mode | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for mode in MODES:
            lines.append(f"| {mode} | " + " | ".join(str(rows[mode].get(c, "-")) for c in cols) + " |")
        lines.append("")
    cols = ["hit@1", "hit@3", "hit@6", "mrr@6"]
    lines += [
        "## Ablation: how much should BM25's ranking count? (library scope)",
        "",
        "| Fusion | " + " | ".join(cols) + " |",
        "|---" * (len(cols) + 1) + "|",
    ]
    for name, row in results["ablation"].items():
        lines.append(f"| {name} | " + " | ".join(str(row[c]) for c in cols) + " |")
    lines += [
        "",
        f"With {meta['questions']} questions, one question is {round(1 / meta['questions'], 3)} of any rate, so differences this small are within noise. "
        "We keep the standard equal-weight fusion rather than tune to this set.",
        "",
    ]
    lines += [
        "`exact` questions reuse a distinctive term from the document (a clause number, a figure, a name); `paraphrase` questions ask in different words.",
        "",
        f"Environment: Python {meta['python']}, {meta['machine']}. Latency is retrieval only (query embedding + scoring), not the LLM.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", default="fastembed", choices=["fastembed", "hashing"])
    args = ap.parse_args()
    s = Settings(_env_file=None)
    embedder = build_embedder(args.embedder, s.embedding_model)
    corpus = build_corpus(embedder, s.chunk_chars, s.chunk_overlap)
    questions = [q for q in load_questions() if q["type"] != "unanswerable"]
    results = {scope: evaluate(corpus, questions, embedder, scope) for scope in ("document", "library")}
    results["ablation"] = evaluate(corpus, questions, embedder, "library", [("hybrid", w) for w in ABLATION_WEIGHTS])
    meta = {
        "date": date.today().isoformat(),
        "embedder": embedder.name,
        "chunk_chars": s.chunk_chars,
        "overlap": s.chunk_overlap,
        "questions": len(questions),
        "documents": len(corpus),
        "pages": sum(len(d.pages) for d in corpus.values()),
        "chunks": sum(len(d.chunks) for d in corpus.values()),
        "python": platform.python_version(),
        "machine": platform.platform(terse=True),
    }
    RESULTS.mkdir(exist_ok=True)
    suffix = "" if args.embedder == "fastembed" else f"-{args.embedder}"
    (RESULTS / f"retrieval{suffix}.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2), encoding="utf-8")
    (RESULTS / f"retrieval{suffix}.md").write_text(to_markdown(meta, results), encoding="utf-8")
    print(to_markdown(meta, results))


if __name__ == "__main__":
    main()
