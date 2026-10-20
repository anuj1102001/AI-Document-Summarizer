"""Page-aware chunking.

Chunks never cross more than one page boundary, carry the page(s) they came from (for citations), and break at
paragraph or sentence boundaries where possible. Headings are detected heuristically and attached to the chunks
below them, which helps both retrieval (the heading is embedded with the text) and the outline view.
"""

import re
from dataclasses import dataclass

from app.ingest.parsers import Page

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    ord: int
    page_start: int
    page_end: int
    text: str
    heading: str | None = None


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not (3 <= len(s) <= 80) or s.endswith((".", ",", ";", ":")) and not re.match(r"^\d+(\.\d+)*\.?\s", s):
        return False
    if re.match(r"^(\d+(\.\d+)*\.?|[IVX]+\.|[A-Z]\.)\s+\S", s):  # "2.1 Scope", "IV. Findings"
        return True
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) > 0.8:
        return True  # ALL CAPS
    words = s.split()
    return 1 <= len(words) <= 8 and all(w[0].isupper() or not w[0].isalpha() for w in words) and not s.endswith("?")


def _split_long(text: str, size: int) -> list[str]:
    """Split text longer than `size` at sentence boundaries (falling back to hard cuts)."""
    out, buf = [], ""
    for sent in _SENTENCE_END.split(text):
        while len(sent) > size:  # a single huge "sentence" (tables, lists without punctuation)
            if buf:
                out.append(buf)
                buf = ""
            cut = sent.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            out.append(sent[:cut])
            sent = sent[cut:].lstrip()
        if len(buf) + len(sent) + 1 > size and buf:
            out.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        out.append(buf)
    return out


def chunk_pages(pages: list[Page], size: int = 1100, overlap: int = 160) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    buf: list[str] = []
    buf_len = 0
    start_page = pages[0].number if pages else 1
    last_page = start_page

    def flush(next_page: int) -> None:
        nonlocal buf, buf_len, start_page
        if not buf:
            start_page = next_page
            return
        text = "\n".join(buf).strip()
        if text:
            chunks.append(Chunk(len(chunks), start_page, last_page, text, heading))
        # Carry a short tail into the next chunk so facts split across a boundary stay retrievable.
        tail = text[-overlap:] if overlap and len(text) > overlap else ""
        tail = tail[tail.find(" ") + 1 :] if " " in tail else tail
        buf, buf_len = ([tail] if tail else []), len(tail)
        start_page = last_page if tail else next_page

    for page in pages:
        if page.number - start_page >= 1 and buf_len > size * 0.5:
            flush(page.number)  # don't let a chunk span more than two pages
        for para in [p for p in page.text.split("\n\n") if p.strip()]:
            first_line = para.split("\n", 1)[0]
            if looks_like_heading(first_line) and len(para) < 120:
                flush(page.number)
                heading = first_line.strip()
                last_page = page.number
                buf, buf_len = [para], len(para)
                start_page = page.number
                continue
            for piece in _split_long(para, size) if len(para) > size else [para]:
                if buf_len + len(piece) > size and buf_len > 0:
                    flush(page.number)
                last_page = page.number
                if not buf:
                    start_page = page.number
                buf.append(piece)
                buf_len += len(piece) + 1
    flush(last_page)
    return [c for c in chunks if len(c.text) > 20 or len(chunks) == 1]
