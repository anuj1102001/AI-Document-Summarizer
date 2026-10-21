"""Check that quotes the model attributes to a document really appear in it.

The model is asked to support every claim with a short verbatim quote and the id of the passage it came from.
We never trust that: each quote is normalised and searched for in the cited passage (and then the whole document,
in case the model cited the wrong passage). The result is shown to the user:

  verified     the quote appears in the cited source, word for word (after normalising whitespace and punctuation)
  approximate  most of the quote's words appear together in the source (paraphrased or OCR-noisy text)
  unverified   the quote wasn't found; the claim is shown with a warning and never presented as stated fact
"""

import re
import unicodedata
from dataclasses import dataclass

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."})
_NON_WORD = re.compile(r"[^a-z0-9%$€£₹.]+")
_WORD = re.compile(r"[a-z0-9%$€£₹]+(?:\.[0-9]+)?")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE).lower()
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    return _NON_WORD.sub(" ", text).strip()


@dataclass
class Verification:
    status: str  # "verified" | "approximate" | "unverified"
    page: int | None = None
    passage_id: str | None = None


def _approx_contains(quote_words: list[str], source_words: list[str], threshold: float = 0.85) -> bool:
    """True if some window of the source contains >= threshold of the quote's words in order-insensitive overlap."""
    n = len(quote_words)
    if n == 0 or len(source_words) == 0:
        return False
    need = set(quote_words)
    window = max(n + n // 3, n)
    for start in range(0, max(1, len(source_words) - n + 1), max(1, n // 4)):
        seg = set(source_words[start : start + window])
        if len(need & seg) / len(need) >= threshold:
            return True
    return False


def verify_quote(
    quote: str, passages: dict[str, tuple[str, int, int]], cited_id: str | None, pages: dict[int, str] | None = None
) -> Verification:
    """passages: {passage_id: (text, page_start, page_end)}; pages: {page_no: text} for exact page lookup."""
    q = normalize(quote)
    if len(q) < 4:
        return Verification("unverified")

    order = ([cited_id] if cited_id in passages else []) + [pid for pid in passages if pid != cited_id]
    for pid in order:
        text, p0, p1 = passages[pid]
        if q in normalize(text):
            return Verification("verified", _page_of(q, pages, p0, p1), pid)

    qw = _WORD.findall(q)
    if len(qw) >= 4:
        for pid in order:
            text, p0, p1 = passages[pid]
            if _approx_contains(qw, _WORD.findall(normalize(text))):
                return Verification("approximate", p0, pid)
    return Verification("unverified")


def _page_of(nq: str, pages: dict[int, str] | None, p0: int, p1: int) -> int:
    if pages:
        for p in range(p0, p1 + 1):
            if p in pages and nq in normalize(pages[p]):
                return p
    return p0


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}
