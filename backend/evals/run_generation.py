"""End-to-end answer evaluation (needs GEMINI_API_KEY in backend/.env; costs a few cents of API usage).

For every question it runs the real Ask pipeline (retrieval + Gemini + citation verification) and measures:
  accuracy          answerable questions whose answer contains every expected fact (string match, case-insensitive)
  correct refusals  unanswerable questions answered with status "not_found"
  false refusals    answerable questions answered with "not_found"
  grounded claims   share of answer claims whose quote was verified (or approximately verified) in the source
  stated-but-unverified  claims the model labelled "stated" whose quote could not be found (a hallucination signal)
  latency and tokens per question

Run from backend/:  python -m evals.run_generation
"""

import json
import statistics
import sys
import tempfile
from datetime import date
from pathlib import Path

from app.config import Settings
from app.db import Database
from app.llm.client import build_llm
from app.retrieval.embeddings import build_embedder
from app.security import create_workspace
from app.services import analysis
from app.services.documents import create_document, index_document
from evals.common import CORPUS, RESULTS, load_questions, md_to_pdf


def answer_text(result: dict) -> str:
    return " ".join(c["text"] for c in result.get("answer", []))


def main() -> None:
    base = Settings()
    if not base.gemini_api_key:
        sys.exit("GEMINI_API_KEY is not set. Add it to backend/.env (never commit it) and run again.")
    with tempfile.TemporaryDirectory() as tmp:
        s = Settings(data_dir=Path(tmp), gemini_api_key=base.gemini_api_key, gemini_model=base.gemini_model)
        db, llm, emb = Database(s.db_path), build_llm(s), build_embedder(s.embedding_backend, s.embedding_model)
        ws, _ = create_workspace(db)
        ids = {}
        for md in sorted(CORPUS.glob("*.md")):
            doc, _ = create_document(db, s, ws, md.stem + ".pdf", md_to_pdf(md.read_text(encoding="utf-8")))
            index_document(db, s, emb, doc["id"])
            ids[md.stem] = doc["id"]

        rows = []
        for q in load_questions():
            r = analysis.ask(db, s, llm, emb, ws, [ids[q["doc"]]], q["question"], [])
            res, meta = r["result"], r["meta"]
            text = answer_text(res).lower()
            rows.append(
                {
                    "id": q["id"],
                    "type": q["type"],
                    "status": res["status"],
                    "correct": all(f.lower() in text for f in q["answer_contains"]) if q["answer_contains"] else res["status"] == "not_found",
                    "claims": res["grounding"].get("claims", 0),
                    "grounded": (res["grounding"].get("verified", 0) + res["grounding"].get("approximate", 0)),
                    "stated_unverified": res["grounding"].get("stated_unverified", 0),
                    "latency_ms": meta["latency_ms"],
                    "tokens": meta["input_tokens"] + meta["output_tokens"],
                    "answer": answer_text(res)[:300],
                }
            )
            print(f"{q['id']:8s} {res['status']:10s} {'OK ' if rows[-1]['correct'] else 'MISS'} {meta['latency_ms']}ms")

    answerable = [r for r in rows if r["type"] != "unanswerable"]
    unanswerable = [r for r in rows if r["type"] == "unanswerable"]
    claims = sum(r["claims"] for r in rows)
    lat = sorted(r["latency_ms"] for r in rows)
    summary = {
        "date": date.today().isoformat(),
        "model": s.gemini_model,
        "questions": len(rows),
        "accuracy": round(sum(r["correct"] for r in answerable) / len(answerable), 3),
        "correct_refusals": round(sum(r["correct"] for r in unanswerable) / len(unanswerable), 3) if unanswerable else None,
        "false_refusals": round(sum(r["status"] == "not_found" for r in answerable) / len(answerable), 3),
        "grounded_claims": round(sum(r["grounded"] for r in rows) / claims, 3) if claims else None,
        "stated_unverified_claims": sum(r["stated_unverified"] for r in rows),
        "latency_p50_ms": lat[len(lat) // 2],
        "latency_p95_ms": lat[int(len(lat) * 0.95) - 1],
        "mean_tokens": round(statistics.mean(r["tokens"] for r in rows)),
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "generation.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    md = ["# Answer evaluation", "", f"Run on {summary['date']} with `{summary['model']}` over {summary['questions']} questions.", "", "| Metric | Value |", "|---|---|"]
    md += [f"| {k.replace('_', ' ')} | {v} |" for k, v in summary.items() if k not in ("date", "model", "questions")]
    md += ["", "Misses:", ""] + [f"- `{r['id']}` ({r['status']}): {r['answer'] or '(no answer)'}" for r in rows if not r["correct"]]
    (RESULTS / "generation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
