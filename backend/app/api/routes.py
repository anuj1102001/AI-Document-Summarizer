from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import Settings
from app.db import Database
from app.deps import get_db, get_embedder, get_llm, get_settings_dep
from app.errors import AppError
from app.llm.client import LLM
from app.retrieval.embeddings import Embedder
from app.security import charge_llm_call, create_workspace, current_workspace
from app.services import analysis
from app.services import documents as docs

router = APIRouter(prefix="/api")


@router.get("/health")
def health(settings: Settings = Depends(get_settings_dep), llm: LLM = Depends(get_llm)):
    return {
        "status": "ok",
        "ai_configured": llm.configured,
        "model": llm.model if llm.configured else None,
        "embedding_model": settings.embedding_model,
    }


@router.post("/workspaces", status_code=201)
def new_workspace(db: Database = Depends(get_db)):
    ws_id, token = create_workspace(db)
    return {"workspace_id": ws_id, "token": token}


# ---- documents ------------------------------------------------------------------------------------------------------


@router.get("/documents")
def list_documents(ws: str = Depends(current_workspace), db: Database = Depends(get_db)):
    return {"documents": docs.list_documents(db, ws)}


@router.post("/documents", status_code=201)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    embedder: Embedder = Depends(get_embedder),
):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)  # read at most one byte past the limit, never the whole oversized body
    document, created = docs.create_document(db, settings, ws, file.filename or "upload", data)
    if created:
        background.add_task(docs.index_document, db, settings, embedder, document["id"])
    return {"document": document, "duplicate": not created}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, ws: str = Depends(current_workspace), db: Database = Depends(get_db)):
    row = docs.get_document(db, ws, doc_id)
    return {"document": docs.public_document(row), "outline": docs.outline(db, doc_id)}


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    doc_id: str, ws: str = Depends(current_workspace), db: Database = Depends(get_db), settings: Settings = Depends(get_settings_dep)
):
    docs.delete_document(db, settings, ws, doc_id)
    return Response(status_code=204)


@router.get("/documents/{doc_id}/pages/{page_no}")
def get_page_text(doc_id: str, page_no: int, ws: str = Depends(current_workspace), db: Database = Depends(get_db)):
    docs.get_document(db, ws, doc_id)
    row = db.one("SELECT page_no, text FROM pages WHERE document_id = ? AND page_no = ?", (doc_id, page_no))
    if not row:
        raise AppError("Page not found.", 404, "NOT_FOUND")
    return {"page": row["page_no"], "text": row["text"]}


@router.get("/documents/{doc_id}/pages/{page_no}/image")
def get_page_image(
    doc_id: str,
    page_no: int,
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    row = docs.get_document(db, ws, doc_id)
    png = docs.render_page(settings, row, page_no)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/documents/{doc_id}/pages/{page_no}/locate")
def locate(
    doc_id: str,
    page_no: int,
    q: str = Query(..., max_length=600),
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    row = docs.get_document(db, ws, doc_id)
    return {"rects": docs.locate_quote(settings, row, page_no, q)}


@router.get("/search")
def search_library(
    q: str = Query(..., min_length=2, max_length=300),
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    embedder: Embedder = Depends(get_embedder),
):
    return {"results": docs.search_library(db, embedder, ws, q)}


# ---- analyses -------------------------------------------------------------------------------------------------------


class RefreshBody(BaseModel):
    refresh: bool = False


class AskBody(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=5)
    question: str = Field(min_length=2, max_length=1000)
    history: list[tuple[str, str]] = Field(default_factory=list, max_length=12)


class CompareBody(BaseModel):
    document_a: str
    document_b: str
    focus: str | None = Field(default=None, max_length=300)
    refresh: bool = False


def _cache_or_charge(
    ws: str, db: Database, settings: Settings, refresh: bool, kind: str, doc_ids: list[str], payload: str, llm: LLM
) -> dict | None:
    """Cached results are free; only real model calls count towards the hourly limit."""
    if not refresh:
        hit = analysis._cached(db, ws, analysis._cache_key(kind, doc_ids, payload, llm.model))
        if hit:
            return hit
    if not llm.configured:
        llm.generate()  # raises a clear "AI not configured" error
    charge_llm_call(ws, db, settings)
    return None


@router.post("/documents/{doc_id}/summary")
def summarize(
    doc_id: str,
    body: RefreshBody = RefreshBody(),
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    llm: LLM = Depends(get_llm),
):
    docs.require_ready(db, ws, [doc_id])
    if hit := _cache_or_charge(ws, db, settings, body.refresh, "summary", [doc_id], "", llm):
        return hit
    return analysis.summarize(db, settings, llm, ws, doc_id, refresh=True)


@router.post("/documents/{doc_id}/extract")
def extract(
    doc_id: str,
    body: RefreshBody = RefreshBody(),
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    llm: LLM = Depends(get_llm),
):
    docs.require_ready(db, ws, [doc_id])
    if hit := _cache_or_charge(ws, db, settings, body.refresh, "extract", [doc_id], "", llm):
        return hit
    return analysis.extract(db, settings, llm, ws, doc_id, refresh=True)


@router.post("/ask")
def ask(
    body: AskBody,
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    llm: LLM = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
):
    docs.require_ready(db, ws, body.document_ids)
    _cache_or_charge(ws, db, settings, True, "qa", body.document_ids, body.question, llm)
    return analysis.ask(db, settings, llm, embedder, ws, body.document_ids, body.question, body.history)


@router.post("/compare")
def compare(
    body: CompareBody,
    ws: str = Depends(current_workspace),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    llm: LLM = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
):
    if body.document_a == body.document_b:
        raise AppError("Pick two different documents to compare.", 422, "SAME_DOCUMENT")
    docs.require_ready(db, ws, [body.document_a, body.document_b])
    if hit := _cache_or_charge(ws, db, settings, body.refresh, "compare", [body.document_a, body.document_b], body.focus or "", llm):
        return hit
    return analysis.compare(db, settings, llm, embedder, ws, body.document_a, body.document_b, body.focus, refresh=True)


@router.get("/history")
def history(document_id: str | None = None, ws: str = Depends(current_workspace), db: Database = Depends(get_db)):
    if document_id:
        docs.get_document(db, ws, document_id)
    return {"analyses": analysis.history(db, ws, document_id)}
