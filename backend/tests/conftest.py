import re
from collections.abc import Callable

import pymupdf
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import Settings
from app.db import Database
from app.deps import get_db, get_embedder, get_llm, get_settings_dep
from app.llm.client import FakeLLM, NotConfiguredLLM
from app.llm.schemas import (
    AnswerOut,
    Citation,
    Claim,
    CompareOut,
    Difference,
    ExtractedItem,
    ExtractOut,
    PartialSummaryOut,
    Section,
    SummaryOut,
)
from app.main import create_app
from app.retrieval.embeddings import HashingEmbedder

PASSAGE = re.compile(r"\[([PAB]\d+)\] \([^)]*\)\n(.*?)(?=\n\n\[[PAB]\d+\] \(|\Z)", re.S)


def passages_in(prompt: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2).strip()) for m in PASSAGE.finditer(prompt)]


def quote_from(text: str, n: int = 8) -> str:
    return " ".join(text.split()[:n])


def claim(label: str, text: str, kind: str = "stated") -> Claim:
    return Claim(text=f"Claim from {label}", kind=kind, citations=[Citation(passage=label, quote=quote_from(text))])


def default_responder(schema: type[BaseModel], prompt: str) -> BaseModel:
    ps = passages_in(prompt)
    first = ps[0] if ps else ("P1", "nothing")
    if schema is SummaryOut:
        return SummaryOut(
            document_type="Test document",
            executive_summary=[claim(*p) for p in ps[:3]],
            key_takeaways=[claim(first[0], first[1], "inferred")],
            sections=[Section(heading="Overview", points=[claim(*p) for p in ps[:2]])],
        )
    if schema is PartialSummaryOut:
        return PartialSummaryOut(points=[claim(*p) for p in ps[:2]])
    if schema is AnswerOut:
        if "unicorn" in prompt.lower():
            return AnswerOut(status="not_found", answer=[], follow_ups=[])
        if "fabricate" in prompt.lower():
            return AnswerOut(
                status="answered",
                answer=[
                    Claim(
                        text="Made up",
                        kind="stated",
                        citations=[Citation(passage=first[0], quote="this sentence does not appear anywhere in the document")],
                    )
                ],
            )
        return AnswerOut(status="answered", answer=[claim(*first)], follow_ups=["What else?"])
    if schema is ExtractOut:
        item = ExtractedItem(
            label="Acme Ltd", detail="Supplier", kind="stated", citations=[Citation(passage=first[0], quote=quote_from(first[1]))]
        )
        return ExtractOut(people_and_organisations=[item])
    if schema is CompareOut:
        a = next((p for p in ps if p[0].startswith("A")), first)
        b = next((p for p in ps if p[0].startswith("B")), first)
        return CompareOut(
            overview=[claim(*a, "inferred")],
            similarities=[claim(*a)],
            differences=[Difference(topic="Term", in_a=claim(*a), in_b=claim(*b))],
            only_in_a=[],
            only_in_b=[claim(*b)],
        )
    raise AssertionError(f"unexpected schema {schema}")


def make_pdf(pages: list[str], password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page(width=595, height=842)
        if text:
            page.insert_textbox(pymupdf.Rect(50, 50, 545, 800), text, fontsize=10)
    kwargs = {"encryption": pymupdf.PDF_ENCRYPT_AES_256, "owner_pw": password, "user_pw": password} if password else {}
    data = doc.tobytes(**kwargs)
    doc.close()
    return data


def make_image_only_pdf() -> bytes:
    """A 'scanned' page: a picture of text, with no text layer."""
    src = pymupdf.open()
    p = src.new_page(width=300, height=200)
    p.insert_text((20, 100), "This is a scanned page", fontsize=14)
    pix = p.get_pixmap()
    src.close()
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_image(page.rect, stream=pix.tobytes("png"))
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, embedding_backend="hashing", gemini_api_key=None, llm_calls_per_hour=1000, _env_file=None)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM(default_responder)


@pytest.fixture
def make_client(settings):
    def build(llm=None) -> TestClient:
        db = Database(settings.db_path)
        embedder = HashingEmbedder()
        app = create_app()
        app.dependency_overrides[get_settings_dep] = lambda: settings
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_embedder] = lambda: embedder
        app.dependency_overrides[get_llm] = lambda: llm or NotConfiguredLLM()
        return TestClient(app)

    return build


@pytest.fixture
def client(make_client, fake_llm) -> TestClient:
    return make_client(fake_llm)


def auth(client: TestClient) -> dict[str, str]:
    token = client.post("/api/workspaces").json()["token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client: TestClient, headers: dict, data: bytes, name: str = "doc.pdf") -> dict:
    r = client.post("/api/documents", headers=headers, files={"file": (name, data, "application/octet-stream")})
    assert r.status_code in (200, 201), r.text
    return r.json()["document"]


Responder = Callable[[type[BaseModel], str], BaseModel]
