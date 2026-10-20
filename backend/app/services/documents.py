"""Document lifecycle: upload -> parse (synchronous, so errors come back immediately) -> chunk and embed (background)
-> ready. Original files are stored under a server-generated name, never the uploaded filename."""

import hashlib
import re

import numpy as np

from app.config import Settings
from app.db import Database, dumps, loads, new_id, now
from app.errors import AppError
from app.ingest.chunking import chunk_pages
from app.ingest.parsers import parse
from app.logging_setup import get_logger
from app.retrieval.embeddings import Embedder
from app.retrieval.search import Candidate

log = get_logger(__name__)
_EXT = {"pdf": ".pdf", "docx": ".docx", "text": ".txt"}


def safe_title(filename: str) -> str:
    base = re.sub(r"[\\/]+", "/", filename).split("/")[-1]
    base = re.sub(r"\.(pdf|docx|txt|md|markdown)$", "", base, flags=re.I)
    base = re.sub(r"[_\-]+", " ", base).strip()
    return (base or "Untitled document")[:120]


def display_filename(filename: str) -> str:
    """The name shown in the UI: last path segment only, no control characters."""
    name = re.split(r"[\\/]", filename or "")[-1]
    return "".join(ch for ch in name if ch.isprintable())[:200] or "upload"


def create_document(db: Database, settings: Settings, ws_id: str, filename: str, data: bytes) -> tuple[dict, bool]:
    """Returns (document, created). Re-uploading an identical file returns the existing document."""
    if len(data) == 0:
        raise AppError("The file is empty.", 422, "EMPTY")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"Files can be up to {settings.max_upload_mb} MB.", 413, "TOO_LARGE")
    sha = hashlib.sha256(data).hexdigest()
    existing = db.one("SELECT * FROM documents WHERE workspace_id = ? AND sha256 = ? AND status != 'failed'", (ws_id, sha))
    if existing:
        return public_document(existing), False

    parsed = parse(data, filename, settings.max_pages)
    doc_id = new_id()
    title = (parsed.title or "").strip() if parsed.title and len(parsed.title.strip()) > 3 else safe_title(filename)
    settings.files_dir.mkdir(parents=True, exist_ok=True)
    (settings.files_dir / f"{doc_id}{_EXT[parsed.kind]}").write_bytes(data)
    with db.tx() as c:
        c.execute(
            """INSERT INTO documents (id, workspace_id, title, filename, kind, size_bytes, sha256, status, page_count, char_count, empty_pages, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'processing', ?, ?, ?, ?)""",
            (
                doc_id,
                ws_id,
                title,
                display_filename(filename),
                parsed.kind,
                len(data),
                sha,
                len(parsed.pages),
                parsed.char_count,
                dumps(parsed.empty_pages),
                now(),
            ),
        )
        c.executemany(
            "INSERT INTO pages (document_id, page_no, text, width, height) VALUES (?, ?, ?, ?, ?)",
            [(doc_id, p.number, p.text, p.width, p.height) for p in parsed.pages],
        )
    log.info(
        "document_parsed",
        extra={
            "document_id": doc_id,
            "kind": parsed.kind,
            "pages": len(parsed.pages),
            "chars": parsed.char_count,
            "empty_pages": len(parsed.empty_pages),
        },
    )
    return public_document(db.one("SELECT * FROM documents WHERE id = ?", (doc_id,))), True


def index_document(db: Database, settings: Settings, embedder: Embedder, doc_id: str) -> None:
    """Chunk and embed. Runs in the background after upload."""
    try:
        from app.ingest.parsers import Page

        rows = db.all("SELECT page_no, text FROM pages WHERE document_id = ? ORDER BY page_no", (doc_id,))
        chunks = chunk_pages([Page(r["page_no"], r["text"]) for r in rows if r["text"]], settings.chunk_chars, settings.chunk_overlap)
        vectors = embedder.embed_passages([f"{c.heading}\n{c.text}" if c.heading else c.text for c in chunks])
        with db.tx() as c:
            c.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            c.executemany(
                "INSERT INTO chunks (id, document_id, ord, page_start, page_end, heading, text, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (new_id(), doc_id, ch.ord, ch.page_start, ch.page_end, ch.heading, ch.text, vectors[i].astype(np.float32).tobytes())
                    for i, ch in enumerate(chunks)
                ],
            )
            c.execute("UPDATE documents SET status = 'ready', error = NULL WHERE id = ?", (doc_id,))
        log.info("document_indexed", extra={"document_id": doc_id, "chunks": len(chunks), "embedder": embedder.name})
    except Exception:
        log.exception("document_index_failed", extra={"document_id": doc_id})
        with db.tx() as c:
            c.execute(
                "UPDATE documents SET status = 'failed', error = ? WHERE id = ?",
                ("We couldn't index this document. Try uploading it again.", doc_id),
            )


def public_document(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "filename": row["filename"],
        "kind": row["kind"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "error": row["error"],
        "page_count": row["page_count"],
        "char_count": row["char_count"],
        "empty_pages": loads(row["empty_pages"], []),
        "page_label": "Page" if row["kind"] == "pdf" else "Part",
        "created_at": row["created_at"],
    }


def get_document(db: Database, ws_id: str, doc_id: str) -> dict:
    row = db.one("SELECT * FROM documents WHERE id = ? AND workspace_id = ?", (doc_id, ws_id))
    if not row:
        raise AppError("Document not found.", 404, "NOT_FOUND")
    return row


def require_ready(db: Database, ws_id: str, doc_ids: list[str]) -> list[dict]:
    docs = [get_document(db, ws_id, d) for d in doc_ids]
    for d in docs:
        if d["status"] == "processing":
            raise AppError(f"“{d['title']}” is still being indexed. Try again in a few seconds.", 409, "NOT_READY")
        if d["status"] == "failed":
            raise AppError(f"“{d['title']}” failed to process.", 409, "FAILED")
    return docs


def list_documents(db: Database, ws_id: str) -> list[dict]:
    return [public_document(r) for r in db.all("SELECT * FROM documents WHERE workspace_id = ? ORDER BY created_at DESC", (ws_id,))]


def delete_document(db: Database, settings: Settings, ws_id: str, doc_id: str) -> None:
    row = get_document(db, ws_id, doc_id)
    with db.tx() as c:
        c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        c.execute("DELETE FROM analyses WHERE workspace_id = ? AND document_ids LIKE ?", (ws_id, f'%"{doc_id}"%'))
    path = settings.files_dir / f"{doc_id}{_EXT[row['kind']]}"
    path.unlink(missing_ok=True)


def candidates(db: Database, doc_ids: list[str], dim: int | None = None) -> list[Candidate]:
    if not doc_ids:
        return []
    marks = ",".join("?" * len(doc_ids))
    rows = db.all(
        f"SELECT id, document_id, text, page_start, page_end, heading, embedding FROM chunks WHERE document_id IN ({marks}) ORDER BY document_id, ord",
        tuple(doc_ids),
    )
    out = []
    for r in rows:
        emb = np.frombuffer(r["embedding"], dtype=np.float32) if r["embedding"] else None
        if emb is not None and dim and emb.shape[0] != dim:
            emb = None  # index built with a different model; fall back to BM25 for this chunk
        out.append(Candidate(r["id"], r["document_id"], r["text"], r["page_start"], r["page_end"], r["heading"], emb))
    return out


def pages_text(db: Database, doc_id: str) -> dict[int, str]:
    return {r["page_no"]: r["text"] for r in db.all("SELECT page_no, text FROM pages WHERE document_id = ?", (doc_id,))}


def outline(db: Database, doc_id: str) -> list[dict]:
    """Free, deterministic outline from detected headings (no LLM call)."""
    rows = db.all(
        "SELECT DISTINCT heading, MIN(page_start) AS page FROM chunks WHERE document_id = ? AND heading IS NOT NULL GROUP BY heading ORDER BY MIN(ord)",
        (doc_id,),
    )
    return [{"heading": r["heading"], "page": r["page"]} for r in rows]


def render_page(settings: Settings, row: dict, page_no: int, zoom: float = 1.6) -> bytes:
    if row["kind"] != "pdf":
        raise AppError("Only PDFs have page images.", 404, "NOT_FOUND")
    import pymupdf

    with pymupdf.open(settings.files_dir / f"{row['id']}.pdf") as doc:
        if not 1 <= page_no <= doc.page_count:
            raise AppError("Page not found.", 404, "NOT_FOUND")
        pix = doc[page_no - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")


def locate_quote(settings: Settings, row: dict, page_no: int, quote: str) -> list[list[float]]:
    """Rectangles (as fractions of the page) covering a quote, for highlighting it over the page image."""
    if row["kind"] != "pdf" or not quote.strip():
        return []
    import pymupdf

    with pymupdf.open(settings.files_dir / f"{row['id']}.pdf") as doc:
        if not 1 <= page_no <= doc.page_count:
            return []
        page = doc[page_no - 1]
        w, h = page.rect.width, page.rect.height
        rects = page.search_for(quote.strip())
        if not rects:  # quotes can wrap differently; fall back to the first 8 words
            rects = page.search_for(" ".join(quote.split()[:8]))
        return [[r.x0 / w, r.y0 / h, r.x1 / w, r.y1 / h] for r in rects]


def search_library(db: Database, embedder: Embedder, ws_id: str, query: str, limit: int = 12) -> list[dict]:
    from app.retrieval.search import search

    docs = db.all("SELECT id, title FROM documents WHERE workspace_id = ? AND status = 'ready'", (ws_id,))
    titles = {d["id"]: d["title"] for d in docs}
    hits = search(candidates(db, list(titles), embedder.dim), query, embedder, k=limit)
    return [
        {
            "document_id": h.candidate.document_id,
            "document_title": titles[h.candidate.document_id],
            "page": h.candidate.page_start,
            "heading": h.candidate.heading,
            "snippet": h.candidate.text[:320],
            "score": round(h.score, 4),
        }
        for h in hits
    ]
