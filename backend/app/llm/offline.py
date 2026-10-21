"""Offline demo "model": builds schema-valid results by copying sentences straight from the passages.

It is not AI and never pretends to be: health reports the model as "offline-demo" and the UI labels its output.
Use it to run the full product locally (UI work, screenshots of empty and error states, CI smoke tests) with no key.
Every claim it produces quotes its source verbatim, so citation verification exercises the real code path.
"""

import re

from pydantic import BaseModel

from app.llm.client import Usage
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
from app.retrieval.search import tokenize

PASSAGE = re.compile(r"\[([PAB]\d+)\] \(([^)]*)\)\n(.*?)(?=\n\n\[[PAB]\d+\] \(|\Z)", re.S)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
DATE = re.compile(
    r"\b(\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}|\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December)\b)"
)
FIGURE = re.compile(
    r"(?:INR|₹|\$|€|£)\s?\d+(?:,\d+)*(?:\.\d+)?(?: (?:lakh|crore))?|\b\d+(?:\.\d+)?%|\b\d+ (?:days|hours|weeks|months|years)\b"
)


def _passages(prompt: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(3).strip()) for m in PASSAGE.finditer(prompt)]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE.split(text.replace("\n", " ")) if len(s.split()) >= 6]


def _claim(label: str, sentence: str, kind: str = "stated") -> Claim:
    words = sentence.split()
    return Claim(text=sentence, kind=kind, citations=[Citation(passage=label, quote=" ".join(words[: min(14, len(words))]))])


def _item(label: str, sentence: str, value: str) -> ExtractedItem:
    i = sentence.find(value)
    start = max(0, sentence.rfind(" ", 0, max(0, i - 40)))
    quote = sentence[start : i + len(value) + 30].strip()
    quote = quote[: quote.rfind(" ")] if len(quote) > len(value) + 10 and " " in quote else quote
    return ExtractedItem(label=value, detail=sentence[:140], kind="stated", citations=[Citation(passage=label, quote=quote or value)])


class OfflineDemoLLM:
    configured = True
    model = "offline-demo"

    def generate(self, *, system: str, prompt: str, schema: type[BaseModel], temperature: float = 0.1, max_output_tokens: int = 4096):
        ps = _passages(prompt)
        firsts = [(label, s[0]) for label, text in ps if (s := _sentences(text))]
        if schema is SummaryOut or schema is PartialSummaryOut:
            claims = [_claim(label, s) for label, s in firsts]
            out = (
                PartialSummaryOut(points=claims[:6])
                if schema is PartialSummaryOut
                else SummaryOut(
                    document_type="Document (offline demo)",
                    executive_summary=claims[:3],
                    key_takeaways=claims[3:6],
                    sections=[
                        Section(heading=f"Passages {i * 4 + 1}–{i * 4 + len(claims[i * 4 : i * 4 + 4])}", points=claims[i * 4 : i * 4 + 4])
                        for i in range((len(claims) + 3) // 4)
                    ],
                )
            )
        elif schema is AnswerOut:
            q = set(tokenize(prompt.split("Question:", 1)[-1].split("\n", 1)[0]))
            scored = sorted(((len(q & set(tokenize(s))), label, s) for label, text in ps for s in _sentences(text)), reverse=True)
            best = [x for x in scored if x[0] > 0][:2]
            out = AnswerOut(status="answered" if best else "not_found", answer=[_claim(label, s) for _, label, s in best], follow_ups=[])
        elif schema is ExtractOut:
            out = ExtractOut()
            for label, text in ps:
                for s in _sentences(text):
                    for m in DATE.finditer(s):
                        out.dates_and_deadlines.append(_item(label, s, m.group(0)))
                    for m in FIGURE.finditer(s):
                        out.figures.append(_item(label, s, m.group(0)))
            out.dates_and_deadlines, out.figures = out.dates_and_deadlines[:12], out.figures[:12]
        elif schema is CompareOut:
            a = [(lb, s) for lb, s in firsts if lb.startswith("A")]
            b = [(lb, s) for lb, s in firsts if lb.startswith("B")]
            out = CompareOut(
                overview=[_claim(*a[0], "inferred")] if a else [],
                similarities=[],
                differences=[
                    Difference(topic=f"Passage {i + 1}", in_a=_claim(*x), in_b=_claim(*y))
                    for i, (x, y) in enumerate(zip(a[:4], b[:4], strict=False))
                ],
                only_in_a=[_claim(*x) for x in a[4:6]],
                only_in_b=[_claim(*y) for y in b[4:6]],
            )
        else:
            raise ValueError(f"offline demo can't produce {schema.__name__}")
        return out, Usage(self.model, len(prompt) // 4, 0, 5)
