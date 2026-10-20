"""AI analyses over documents: summary, question answering, extraction and comparison.

Pipeline for every analysis:
  1. choose passages (whole document for summaries and extraction when it fits; hybrid retrieval for questions)
  2. label them (P1, P2... / A1, B1...) so the model cites short labels instead of long ids
  3. call the model for a schema-validated result
  4. ground it: resolve every citation, verify its quote against the source, attach page numbers
  5. cache by (kind, documents, input, prompt version, model) so repeat views cost nothing
"""

import hashlib
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.db import Database, dumps, loads, new_id, now
from app.grounding import verify_quote
from app.llm import prompts
from app.llm.client import LLM, Usage
from app.llm.schemas import AnswerOut, CompareOut, ExtractOut, PartialSummaryOut, SummaryOut
from app.retrieval.embeddings import Embedder
from app.retrieval.search import Candidate, search
from app.services.documents import candidates, outline, pages_text, require_ready

STATUS_RANK = {"verified": 2, "approximate": 1, "unverified": 0}


class Labeled:
    """Passage labels -> chunks, for prompting and for resolving citations afterwards."""

    def __init__(self) -> None:
        self.by_label: dict[str, Candidate] = {}
        self.doc_pages: dict[str, dict[int, str]] = {}

    def add(self, prefix: str, chunks: list[Candidate], page_label: str) -> list[tuple[str, str, str]]:
        out = []
        for c in chunks:
            label = f"{prefix}{sum(1 for k in self.by_label if k.startswith(prefix) and k[len(prefix) :].isdigit()) + 1}"
            self.by_label[label] = c
            loc = f"{page_label} {c.page_start}" + (f"-{c.page_end}" if c.page_end != c.page_start else "")
            if c.heading:
                loc += f" · {c.heading}"
            out.append((label, loc, c.text))
        return out


def ground(result: Any, labeled: Labeled, db: Database) -> tuple[Any, dict]:
    """Walk the result; enrich every citation and score every claim-like object. Returns (result, stats)."""
    stats = {"claims": 0, "verified": 0, "approximate": 0, "unverified": 0, "stated_unverified": 0}
    passages = {label: (c.text, c.page_start, c.page_end) for label, c in labeled.by_label.items()}

    def pages_for(doc_id: str) -> dict[int, str]:
        if doc_id not in labeled.doc_pages:
            labeled.doc_pages[doc_id] = pages_text(db, doc_id)
        return labeled.doc_pages[doc_id]

    def visit(node: Any) -> Any:
        if isinstance(node, list):
            return [visit(n) for n in node]
        if not isinstance(node, dict):
            return node
        node = {k: visit(v) for k, v in node.items()}
        if "citations" in node and isinstance(node["citations"], list):
            best = "unverified"
            enriched = []
            for cit in node["citations"]:
                label = (cit.get("passage") or "").strip().strip("[]")
                chunk = labeled.by_label.get(label)
                v = verify_quote(cit.get("quote", ""), passages, label if chunk else None, pages_for(chunk.document_id) if chunk else None)
                src = labeled.by_label.get(v.passage_id) if v.passage_id else chunk
                enriched.append(
                    {
                        "quote": cit.get("quote", ""),
                        "status": v.status,
                        "document_id": src.document_id if src else None,
                        "page": v.page if v.page else (src.page_start if src else None),
                        "chunk_id": src.id if src else None,
                    }
                )
                if STATUS_RANK[v.status] > STATUS_RANK[best]:
                    best = v.status
            node["citations"] = enriched
            node["support"] = best
            stats["claims"] += 1
            stats[best] += 1
            if node.get("kind") == "stated" and best == "unverified":
                stats["stated_unverified"] += 1
        return node

    out = visit(result)
    stats["grounded_rate"] = round((stats["verified"] + stats["approximate"]) / stats["claims"], 3) if stats["claims"] else None
    return out, stats


def _cache_key(kind: str, doc_ids: list[str], payload: str, model: str) -> str:
    raw = "|".join([kind, ",".join(doc_ids), payload, prompts.PROMPT_VERSION, model])
    return hashlib.sha256(raw.encode()).hexdigest()


def _cached(db: Database, ws_id: str, key: str) -> dict | None:
    row = db.one("SELECT * FROM analyses WHERE workspace_id = ? AND cache_key = ? ORDER BY created_at DESC LIMIT 1", (ws_id, key))
    return _public(row, cached=True) if row else None


def _public(row: dict, cached: bool = False) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "document_ids": loads(row["document_ids"], []),
        "input": loads(row["input"]),
        "result": loads(row["result"]),
        "meta": {
            "model": row["model"],
            "prompt_version": row["prompt_version"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "latency_ms": row["latency_ms"],
            "cached": cached,
            "created_at": row["created_at"],
        },
    }


def _save(db: Database, ws_id: str, kind: str, key: str, doc_ids: list[str], inp: Any, result: dict, usage: Usage) -> dict:
    row = {
        "id": new_id(),
        "workspace_id": ws_id,
        "kind": kind,
        "cache_key": key,
        "document_ids": dumps(doc_ids),
        "input": dumps(inp),
        "result": dumps(result),
        "model": usage.model,
        "prompt_version": prompts.PROMPT_VERSION,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
        "created_at": now(),
    }
    with db.tx() as c:
        c.execute(f"INSERT INTO analyses ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
    return _public(row)


def _sum_usage(usages: list[Usage], model: str) -> Usage:
    return Usage(model, sum(u.input_tokens for u in usages), sum(u.output_tokens for u in usages), sum(u.latency_ms for u in usages))


def _label_for(doc: dict) -> str:
    return "Page" if doc["kind"] == "pdf" else "Part"


def _finish(result: BaseModel | dict, labeled: Labeled, db: Database, extra: dict | None = None) -> dict:
    data = result.model_dump() if isinstance(result, BaseModel) else result
    grounded, stats = ground(data, labeled, db)
    grounded["grounding"] = stats
    if extra:
        grounded.update(extra)
    return grounded


# ---------------------------------------------------------------------------------------------------------------------


def summarize(db: Database, settings: Settings, llm: LLM, ws_id: str, doc_id: str, refresh: bool = False) -> dict:
    (doc,) = require_ready(db, ws_id, [doc_id])
    key = _cache_key("summary", [doc_id], "", llm.model)
    if not refresh and (hit := _cached(db, ws_id, key)):
        return hit

    chunks = candidates(db, [doc_id])
    labeled = Labeled()
    total_chars = sum(len(c.text) for c in chunks)

    if total_chars <= settings.single_pass_chars:
        passages = labeled.add("P", chunks, _label_for(doc))
        out, usage = llm.generate(
            system=prompts.SYSTEM, prompt=prompts.summary_prompt(doc["title"], passages), schema=SummaryOut, max_output_tokens=6000
        )
        strategy, usages = "single_pass", [usage]
    else:
        # Map-reduce: summarise slices, keep only grounded points, then summarise the points.
        usages, points = [], []
        slices = _slices(chunks, settings.single_pass_chars // 2)
        for i, sl in enumerate(slices, start=1):
            part_labeled = Labeled()
            passages = part_labeled.add("P", sl, _label_for(doc))
            part, u = llm.generate(
                system=prompts.SYSTEM,
                prompt=prompts.partial_summary_prompt(doc["title"], f"part {i} of {len(slices)}", passages),
                schema=PartialSummaryOut,
            )
            usages.append(u)
            grounded, _ = ground(part.model_dump(), part_labeled, db)
            for p in grounded["points"]:
                if p["support"] != "unverified":
                    cit = p["citations"][0]
                    src = next(c for c in sl if c.id == cit["chunk_id"])
                    points.append(
                        Candidate(
                            f"pt-{len(points)}",
                            src.document_id,
                            p["text"] + " — “" + cit["quote"] + "”",
                            cit["page"] or src.page_start,
                            cit["page"] or src.page_end,
                            src.heading,
                            None,
                        )
                    )
        passages = labeled.add("P", points, _label_for(doc))
        out, u = llm.generate(
            system=prompts.SYSTEM, prompt=prompts.reduce_summary_prompt(doc["title"], passages), schema=SummaryOut, max_output_tokens=6000
        )
        usages.append(u)
        strategy = f"map_reduce ({len(slices)} parts)"

    result = _finish(out, labeled, db, {"outline": outline(db, doc_id), "strategy": strategy})
    return _save(db, ws_id, "summary", key, [doc_id], None, result, _sum_usage(usages, llm.model))


def _slices(chunks: list[Candidate], max_chars: int) -> list[list[Candidate]]:
    out, cur, n = [], [], 0
    for c in chunks:
        if n + len(c.text) > max_chars and cur:
            out.append(cur)
            cur, n = [], 0
        cur.append(c)
        n += len(c.text)
    if cur:
        out.append(cur)
    return out


def ask(
    db: Database,
    settings: Settings,
    llm: LLM,
    embedder: Embedder,
    ws_id: str,
    doc_ids: list[str],
    question: str,
    history: list[tuple[str, str]],
) -> dict:
    docs = require_ready(db, ws_id, doc_ids)
    question = question.strip()
    hits = search(candidates(db, doc_ids, embedder.dim), question, embedder, k=settings.retrieval_k)
    labeled = Labeled()
    titles = {d["id"]: d for d in docs}
    passages = []
    for h in hits:
        c = h.candidate
        passages += labeled.add("P", [c], _label_for(titles[c.document_id]))
    retrieval = [
        {
            "label": label,
            "document_id": c.document_id,
            "page": c.page_start,
            "heading": c.heading,
            "dense_rank": h.dense_rank,
            "sparse_rank": h.sparse_rank,
        }
        for (label, _, _), h, c in zip(passages, hits, [h.candidate for h in hits], strict=True)
    ]
    if not hits:
        result = {"status": "not_found", "answer": [], "follow_ups": [], "grounding": {"claims": 0, "grounded_rate": None}, "retrieval": []}
        return _save(db, ws_id, "qa", new_id(), doc_ids, {"question": question}, result, Usage(llm.model))
    out, usage = llm.generate(system=prompts.SYSTEM, prompt=prompts.answer_prompt(question, passages, history), schema=AnswerOut)
    result = _finish(out, labeled, db, {"retrieval": retrieval})
    # Questions aren't cached (conversations differ), but are kept so the user can revisit them.
    return _save(db, ws_id, "qa", new_id(), doc_ids, {"question": question}, result, usage)


def extract(db: Database, settings: Settings, llm: LLM, ws_id: str, doc_id: str, refresh: bool = False) -> dict:
    (doc,) = require_ready(db, ws_id, [doc_id])
    key = _cache_key("extract", [doc_id], "", llm.model)
    if not refresh and (hit := _cached(db, ws_id, key)):
        return hit
    chunks = candidates(db, [doc_id])
    labeled = Labeled()
    usages, merged = [], ExtractOut()
    for sl in _slices(chunks, settings.single_pass_chars):
        part_labeled = labeled
        passages = part_labeled.add("P", sl, _label_for(doc))
        out, u = llm.generate(
            system=prompts.SYSTEM, prompt=prompts.extract_prompt(doc["title"], passages), schema=ExtractOut, max_output_tokens=6000
        )
        usages.append(u)
        for field in ExtractOut.model_fields:
            getattr(merged, field).extend(getattr(out, field))
    result = _finish(merged, labeled, db)
    return _save(db, ws_id, "extract", key, [doc_id], None, result, _sum_usage(usages, llm.model))


def compare(
    db: Database,
    settings: Settings,
    llm: LLM,
    embedder: Embedder,
    ws_id: str,
    doc_a: str,
    doc_b: str,
    focus: str | None,
    refresh: bool = False,
) -> dict:
    a, b = require_ready(db, ws_id, [doc_a, doc_b])
    key = _cache_key("compare", [doc_a, doc_b], focus or "", llm.model)
    if not refresh and (hit := _cached(db, ws_id, key)):
        return hit
    budget = settings.single_pass_chars // 2

    def pick(doc_id: str) -> list[Candidate]:
        chunks = candidates(db, [doc_id], embedder.dim)
        if sum(len(c.text) for c in chunks) <= budget:
            return chunks
        # Too long to send whole: keep the passages most relevant to the focus (or to a generic comparison query).
        k = max(8, budget // max(1, settings.chunk_chars))
        hits = search(chunks, focus or "main terms obligations scope dates amounts conclusions", embedder, k=k)
        return sorted([h.candidate for h in hits], key=lambda c: (c.page_start, c.id))

    labeled = Labeled()
    pa = labeled.add("A", pick(doc_a), _label_for(a))
    pb = labeled.add("B", pick(doc_b), _label_for(b))
    out, usage = llm.generate(
        system=prompts.SYSTEM,
        prompt=prompts.compare_prompt(a["title"], b["title"], pa, pb, focus),
        schema=CompareOut,
        max_output_tokens=6000,
    )
    result = _finish(out, labeled, db)
    return _save(db, ws_id, "compare", key, [doc_a, doc_b], {"focus": focus}, result, usage)


def history(db: Database, ws_id: str, doc_id: str | None = None, limit: int = 50) -> list[dict]:
    if doc_id:
        rows = db.all(
            "SELECT * FROM analyses WHERE workspace_id = ? AND document_ids LIKE ? ORDER BY created_at DESC LIMIT ?",
            (ws_id, f'%"{doc_id}"%', limit),
        )
    else:
        rows = db.all("SELECT * FROM analyses WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?", (ws_id, limit))
    return [_public(r) for r in rows]
