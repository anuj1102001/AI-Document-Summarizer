"""Shared helpers for the evaluation scripts: build the corpus through the real ingestion pipeline."""

import json
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.ingest.chunking import chunk_pages
from app.ingest.parsers import parse
from app.retrieval.embeddings import Embedder
from app.retrieval.search import Candidate

EVAL_DIR = Path(__file__).parent
CORPUS = EVAL_DIR / "corpus"
RESULTS = EVAL_DIR / "results"


def md_to_pdf(md: str) -> bytes:
    """Render markdown-ish text to a real PDF, one page per form-feed marker, so evals exercise PDF parsing too."""
    doc = pymupdf.open()
    for page_text in md.split("\\f"):
        text = "\n".join(line.lstrip("# ") for line in page_text.strip().split("\n"))
        page = doc.new_page(width=595, height=842)
        overflow = page.insert_textbox(pymupdf.Rect(56, 56, 539, 800), text, fontsize=9.5, fontname="helv")
        if overflow < 0:
            raise ValueError("Page text overflowed; split it with another \\f marker.")
    data = doc.tobytes()
    doc.close()
    return data


@dataclass
class CorpusDoc:
    name: str
    pdf: bytes
    pages: dict[int, str]
    chunks: list[Candidate]


def build_corpus(embedder: Embedder, chunk_chars: int = 1100, overlap: int = 160) -> dict[str, CorpusDoc]:
    out = {}
    for md_path in sorted(CORPUS.glob("*.md")):
        pdf = md_to_pdf(md_path.read_text(encoding="utf-8"))
        parsed = parse(pdf, md_path.stem + ".pdf", 500)
        chunks = chunk_pages(parsed.pages, chunk_chars, overlap)
        vecs = embedder.embed_passages([f"{c.heading}\n{c.text}" if c.heading else c.text for c in chunks])
        cands = [Candidate(f"{md_path.stem}-{c.ord}", md_path.stem, c.text, c.page_start, c.page_end, c.heading, vecs[i]) for i, c in enumerate(chunks)]
        out[md_path.stem] = CorpusDoc(md_path.stem, pdf, {p.number: p.text for p in parsed.pages}, cands)
    return out


def load_questions() -> list[dict]:
    return [json.loads(line) for line in (EVAL_DIR / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
