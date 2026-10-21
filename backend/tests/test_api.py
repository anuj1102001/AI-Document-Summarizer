from app.llm.client import FakeLLM
from tests.conftest import auth, default_responder, make_pdf, upload

CONTRACT = [
    "1. Services\n\nAcme Ltd will provide cloud hosting services to Globex from 1 January 2026.",
    "2. Fees\n\nGlobex shall pay a monthly fee of $4,000, invoiced on the first business day of each month.",
    "3. Termination\n\nEither party may terminate with 60 days written notice. Late payments incur 1.5% monthly interest.",
]


def test_workspace_token_is_required(client):
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/documents", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_workspaces_are_isolated(client):
    a, b = auth(client), auth(client)
    doc = upload(client, a, make_pdf(CONTRACT))
    assert client.get(f"/api/documents/{doc['id']}", headers=b).status_code == 404
    assert client.get("/api/documents", headers=b).json()["documents"] == []
    assert client.post(f"/api/documents/{doc['id']}/summary", headers=b).status_code == 404


def test_upload_indexes_in_background_and_dedupes(client):
    h = auth(client)
    pdf = make_pdf(CONTRACT)
    doc = upload(client, h, pdf, "Hosting Agreement v2.pdf")
    assert doc["title"] == "Hosting Agreement v2" and doc["page_count"] == 3
    detail = client.get(f"/api/documents/{doc['id']}", headers=h).json()
    assert detail["document"]["status"] == "ready"
    assert [o["heading"] for o in detail["outline"]] == ["1. Services", "2. Fees", "3. Termination"]
    again = client.post("/api/documents", headers=h, files={"file": ("copy.pdf", pdf)}).json()
    assert again["duplicate"] is True and again["document"]["id"] == doc["id"]


def test_upload_rejections(client, settings):
    h = auth(client)
    r = client.post("/api/documents", headers=h, files={"file": ("x.pdf", b"not a pdf at all")})
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_TYPE"
    settings.max_upload_mb = 0
    r = client.post("/api/documents", headers=h, files={"file": ("big.pdf", make_pdf(CONTRACT))})
    assert r.status_code == 413


def test_uploaded_filename_cannot_escape_storage(client, settings):
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT), "../../../etc/passwd.pdf")
    assert doc["filename"] == "passwd.pdf"
    stored = list(settings.files_dir.iterdir())
    assert [p.name for p in stored] == [f"{doc['id']}.pdf"]


def test_summary_is_grounded_and_cached(client, fake_llm):
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT))
    first = client.post(f"/api/documents/{doc['id']}/summary", headers=h).json()
    res = first["result"]
    assert res["document_type"] == "Test document"
    cit = res["executive_summary"][0]["citations"][0]
    assert cit["status"] == "verified" and cit["page"] in (1, 2, 3) and cit["document_id"] == doc["id"]
    assert res["grounding"]["grounded_rate"] == 1.0
    assert res["key_takeaways"][0]["kind"] == "inferred"
    assert first["meta"]["cached"] is False
    calls = len(fake_llm.calls)
    second = client.post(f"/api/documents/{doc['id']}/summary", headers=h).json()
    assert second["meta"]["cached"] is True and len(fake_llm.calls) == calls
    refreshed = client.post(f"/api/documents/{doc['id']}/summary", headers=h, json={"refresh": True}).json()
    assert refreshed["meta"]["cached"] is False and len(fake_llm.calls) == calls + 1


def test_long_documents_use_map_reduce(client, settings, fake_llm):
    settings.single_pass_chars = 400
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT * 3))
    res = client.post(f"/api/documents/{doc['id']}/summary", headers=h).json()["result"]
    assert res["strategy"].startswith("map_reduce")
    assert sum(1 for name, _ in fake_llm.calls if name == "PartialSummaryOut") >= 2
    assert res["grounding"]["claims"] > 0


def test_question_answering_with_citations_and_retrieval_trace(client):
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT))
    r = client.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "How much is the monthly fee?"}).json()
    res = r["result"]
    assert res["status"] == "answered" and res["answer"][0]["support"] == "verified"
    assert res["retrieval"] and res["retrieval"][0]["label"] == "P1"
    assert r["input"]["question"] == "How much is the monthly fee?"


def test_not_found_and_fabricated_quotes_are_flagged(client):
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT))
    nf = client.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "Does it mention a unicorn?"}).json()["result"]
    assert nf["status"] == "not_found" and nf["answer"] == []
    fab = client.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "fabricate an answer about fees"}).json()[
        "result"
    ]
    assert fab["answer"][0]["support"] == "unverified"
    assert fab["grounding"]["stated_unverified"] == 1


def test_extract_and_compare(client):
    h = auth(client)
    a = upload(client, h, make_pdf(CONTRACT), "v1.pdf")
    b = upload(client, h, make_pdf([p.replace("60 days", "30 days") for p in CONTRACT]), "v2.pdf")
    ex = client.post(f"/api/documents/{a['id']}/extract", headers=h).json()["result"]
    assert ex["people_and_organisations"][0]["support"] == "verified"
    cmp = client.post("/api/compare", headers=h, json={"document_a": a["id"], "document_b": b["id"]}).json()["result"]
    diff = cmp["differences"][0]
    assert diff["in_a"]["citations"][0]["document_id"] == a["id"]
    assert diff["in_b"]["citations"][0]["document_id"] == b["id"]
    same = client.post("/api/compare", headers=h, json={"document_a": a["id"], "document_b": a["id"]})
    assert same.status_code == 422


def test_ai_not_configured_is_a_clear_503(make_client):
    c = make_client(None)
    h = auth(c)
    doc = upload(c, h, make_pdf(CONTRACT))
    r = c.post(f"/api/documents/{doc['id']}/summary", headers=h)
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_NOT_CONFIGURED"
    # everything that doesn't need the model still works
    assert c.get("/api/search", headers=h, params={"q": "monthly fee"}).json()["results"]


def test_rate_limit_counts_only_real_model_calls(make_client, settings):
    settings.llm_calls_per_hour = 2
    c = make_client(FakeLLM(default_responder))
    h = auth(c)
    doc = upload(c, h, make_pdf(CONTRACT))
    assert c.post(f"/api/documents/{doc['id']}/summary", headers=h).status_code == 200
    assert c.post(f"/api/documents/{doc['id']}/summary", headers=h).status_code == 200  # cached: free
    assert c.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "fee?"}).status_code == 200
    r = c.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "notice?"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_page_image_locate_search_history_and_delete(client, settings):
    h = auth(client)
    doc = upload(client, h, make_pdf(CONTRACT))
    img = client.get(f"/api/documents/{doc['id']}/pages/2/image", headers=h)
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    rects = client.get(f"/api/documents/{doc['id']}/pages/2/locate", headers=h, params={"q": "monthly fee of $4,000"}).json()["rects"]
    assert rects and all(0 <= v <= 1 for r in rects for v in r)
    hits = client.get("/api/search", headers=h, params={"q": "termination notice"}).json()["results"]
    assert hits[0]["page"] == 3
    client.post(f"/api/documents/{doc['id']}/summary", headers=h)
    assert len(client.get("/api/history", headers=h, params={"document_id": doc["id"]}).json()["analyses"]) == 1
    assert client.delete(f"/api/documents/{doc['id']}", headers=h).status_code == 204
    assert client.get(f"/api/documents/{doc['id']}", headers=h).status_code == 404
    assert list(settings.files_dir.iterdir()) == []
    assert client.get("/api/history", headers=h).json()["analyses"] == []


def test_errors_never_leak_internals(client):
    h = auth(client)
    r = client.post("/api/ask", headers=h, json={"document_ids": [], "question": "x"})
    assert r.status_code == 422 and "error" in r.json() and "Traceback" not in r.text


def test_offline_demo_mode_produces_grounded_results_and_says_what_it_is(make_client, settings):
    from app.llm.offline import OfflineDemoLLM

    c = make_client(OfflineDemoLLM())
    h = auth(c)
    doc = upload(c, h, make_pdf(CONTRACT))
    assert c.get("/api/health").json()["model"] == "offline-demo"
    summary = c.post(f"/api/documents/{doc['id']}/summary", headers=h).json()["result"]
    assert summary["grounding"]["grounded_rate"] == 1.0
    answer = c.post("/api/ask", headers=h, json={"document_ids": [doc["id"]], "question": "What is the monthly fee?"}).json()["result"]
    assert "4,000" in answer["answer"][0]["text"]
    facts = c.post(f"/api/documents/{doc['id']}/extract", headers=h).json()["result"]
    assert any(f["label"] == "$4,000" for f in facts["figures"])
    assert all(f["support"] == "verified" for f in facts["figures"])
