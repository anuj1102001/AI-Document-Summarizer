from app.grounding import normalize, verify_quote
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.search import Candidate, rrf, search, tokenize

PASSAGES = {
    "P1": ("The Supplier shall deliver the goods within 14 days of the order date.", 1, 1),
    "P2": ("Either party may terminate this Agreement with ninety (90) days' written notice.", 2, 2),
    "P3": ("The total contract value is ₹12,50,000 including GST, payable in two instalments.", 3, 3),
}


def test_exact_quote_is_verified_with_page():
    v = verify_quote("deliver the goods within 14 days", PASSAGES, "P1")
    assert v.status == "verified" and v.passage_id == "P1" and v.page == 1


def test_normalisation_tolerates_curly_quotes_dashes_and_case():
    v = verify_quote("ninety (90) days’ written notice", PASSAGES, "P2")
    assert v.status == "verified"
    assert normalize("Two—Party “Notice”") == normalize('two-party "notice"')


def test_wrong_citation_is_corrected_to_the_real_passage():
    v = verify_quote("payable in two instalments", PASSAGES, "P1")
    assert v.status == "verified" and v.passage_id == "P3" and v.page == 3


def test_paraphrase_is_only_approximate():
    v = verify_quote("either party may terminate the Agreement with ninety days written notice", PASSAGES, "P2")
    assert v.status == "approximate"


def test_invented_quote_is_unverified():
    v = verify_quote("the supplier will refund all payments in full", PASSAGES, "P1")
    assert v.status == "unverified" and v.page is None


def test_numbers_must_match_exactly():
    assert verify_quote("total contract value is ₹12,50,000", PASSAGES, "P3").status == "verified"
    assert verify_quote("total contract value is ₹13,50,000", PASSAGES, "P3").status != "verified"


def _cands(texts: list[str]) -> list[Candidate]:
    emb = HashingEmbedder()
    vecs = emb.embed_passages(texts)
    return [Candidate(f"c{i}", "d", t, i + 1, i + 1, None, vecs[i]) for i, t in enumerate(texts)]


def test_rrf_rewards_agreement_between_rankings():
    scores = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert max(scores, key=scores.get) in {"a", "b"} and scores["d"] < scores["a"]


def test_hybrid_finds_exact_identifier_tokens():
    cands = _cands(
        [
            "General terms of service and conditions.",
            "Clause 7.3 sets the liability cap at the annual fees.",
            "Contact the support team by email.",
        ]
    )
    hits = search(cands, "what does clause 7.3 say", HashingEmbedder(), k=2)
    assert hits[0].candidate.id == "c1"
    assert hits[0].sparse_rank == 1


def test_tokenize_keeps_codes_and_drops_stopwords():
    assert tokenize("What is the SLA for INV-2024.07?") == ["sla", "inv-2024.07"]


def test_empty_inputs():
    assert search([], "anything", HashingEmbedder()) == []
    assert search(_cands(["text"]), "   ", HashingEmbedder()) == []
