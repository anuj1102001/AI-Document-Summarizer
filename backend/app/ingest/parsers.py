"""Turn an uploaded file into clean per-page text.

Supported: PDF (with real page numbers), DOCX and plain text / Markdown (split into ~3,000-character "parts",
because those formats have no pages). The file type is decided from the bytes, not the filename.
"""

import io
import re
import unicodedata
from dataclasses import dataclass, field

import pymupdf

from app.errors import AppError

# A page with less text than this is treated as empty (blank, image-only or scanned).
MIN_PAGE_CHARS = 25
PART_CHARS = 3000


@dataclass
class Page:
    number: int  # 1-based
    text: str
    width: float | None = None
    height: float | None = None


@dataclass
class ParsedDocument:
    kind: str  # "pdf" | "docx" | "text"
    pages: list[Page]
    title: str | None = None
    empty_pages: list[int] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)


def detect_kind(data: bytes, filename: str) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:4] == b"PK\x03\x04":
        if b"word/" in data[:4000] or filename.lower().endswith(".docx"):
            return "docx"
        raise AppError("This looks like a zip or Office file other than Word. Upload a PDF, DOCX, TXT or MD file.", 415, "UNSUPPORTED_TYPE")
    if filename.lower().endswith((".txt", ".md", ".markdown")):
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise AppError("This text file isn't UTF-8 encoded. Save it as UTF-8 and try again.", 415, "BAD_ENCODING") from None
        return "text"
    raise AppError("Unsupported file type. Upload a PDF, DOCX, TXT or MD file.", 415, "UNSUPPORTED_TYPE")


_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SPACES = re.compile(r"[ \t ]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("­", "")  # soft hyphens
    text = _HYPHEN_BREAK.sub(r"\1\2", text)  # "infor-\nmation" -> "information"
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _MANY_NEWLINES.sub("\n\n", text).strip()


def parse_pdf(data: bytes, max_pages: int) -> ParsedDocument:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise AppError("This PDF couldn't be opened. It may be damaged.", 422, "CORRUPT_FILE") from None
    with doc:
        if doc.needs_pass:
            raise AppError("This PDF is password-protected. Remove the password and upload it again.", 422, "ENCRYPTED")
        if doc.page_count == 0:
            raise AppError("This PDF has no pages.", 422, "EMPTY")
        if doc.page_count > max_pages:
            raise AppError(f"This PDF has {doc.page_count} pages; the limit is {max_pages}.", 413, "TOO_MANY_PAGES")
        pages, empty = [], []
        for i, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text", sort=True))
            if len(text) < MIN_PAGE_CHARS:
                empty.append(i)
            pages.append(Page(i, text, page.rect.width, page.rect.height))
        title = (doc.metadata or {}).get("title") or None
    return ParsedDocument("pdf", pages, title=title, empty_pages=empty)


def _split_parts(text: str) -> list[Page]:
    """Group paragraphs into ~PART_CHARS parts so formats without pages still get precise citations."""
    parts, buf, n = [], [], 0
    for para in text.split("\n\n"):
        if n + len(para) > PART_CHARS and buf:
            parts.append("\n\n".join(buf))
            buf, n = [], 0
        buf.append(para)
        n += len(para) + 2
    if buf:
        parts.append("\n\n".join(buf))
    return [Page(i, p) for i, p in enumerate(parts, start=1)]


def parse_docx(data: bytes) -> ParsedDocument:
    import docx  # python-docx

    try:
        d = docx.Document(io.BytesIO(data))
    except Exception:
        raise AppError("This Word file couldn't be opened. It may be damaged.", 422, "CORRUPT_FILE") from None
    blocks = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                blocks.append(" | ".join(cells))
    text = clean_text("\n\n".join(blocks))
    title = d.core_properties.title or None
    return ParsedDocument("docx", _split_parts(text), title=title)


def parse_text(data: bytes) -> ParsedDocument:
    return ParsedDocument("text", _split_parts(clean_text(data.decode("utf-8"))))


def parse(data: bytes, filename: str, max_pages: int) -> ParsedDocument:
    kind = detect_kind(data, filename)
    parsed = {"pdf": lambda: parse_pdf(data, max_pages), "docx": lambda: parse_docx(data), "text": lambda: parse_text(data)}[kind]()
    if parsed.char_count < MIN_PAGE_CHARS:
        if kind == "pdf":
            raise AppError(
                "No selectable text was found. This looks like a scanned or image-only PDF, and text recognition (OCR) isn't supported yet.",
                422,
                "NO_TEXT",
            )
        raise AppError("This file has no readable text.", 422, "NO_TEXT")
    return parsed
