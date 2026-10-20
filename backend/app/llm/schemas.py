"""Structured outputs requested from the model. Kept deliberately flat: deep nesting hurts schema adherence."""

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    passage: str = Field(description="The passage label exactly as given, e.g. P3 or A2.")
    quote: str = Field(description="A short verbatim quote (5-30 words) copied exactly from that passage.")


class Claim(BaseModel):
    text: str = Field(description="One self-contained statement.")
    kind: Literal["stated", "inferred"] = Field(description="stated: the document says this. inferred: your interpretation or synthesis.")
    citations: list[Citation] = Field(default_factory=list)


class Section(BaseModel):
    heading: str
    points: list[Claim]


class SummaryOut(BaseModel):
    document_type: str = Field(description="What kind of document this is, in 2-6 words, e.g. 'Vendor services agreement'.")
    executive_summary: list[Claim] = Field(description="3-5 claims a busy reader needs first.")
    key_takeaways: list[Claim] = Field(description="3-7 actionable or decision-relevant takeaways.")
    sections: list[Section] = Field(description="Detailed summary: one entry per major part of the document, in document order.")


class PartialSummaryOut(BaseModel):
    """Map step for long documents: a summary of one slice."""

    points: list[Claim]


class AnswerOut(BaseModel):
    status: Literal["answered", "partial", "not_found"] = Field(
        description="answered: fully supported by the passages. partial: only partly supported. not_found: the passages don't contain the answer."
    )
    answer: list[Claim] = Field(description="The answer as 1-5 claims. Empty when not_found.")
    follow_ups: list[str] = Field(default_factory=list, description="Up to 3 follow-up questions the passages could answer.")


class ExtractedItem(BaseModel):
    label: str = Field(description="The thing itself, e.g. a name, a date, an amount or a short action.")
    detail: str = Field(description="One line of context: what it refers to.")
    kind: Literal["stated", "inferred"]
    citations: list[Citation]


class ExtractOut(BaseModel):
    people_and_organisations: list[ExtractedItem] = Field(default_factory=list)
    dates_and_deadlines: list[ExtractedItem] = Field(default_factory=list)
    figures: list[ExtractedItem] = Field(default_factory=list, description="Amounts, percentages, quantities and metrics.")
    decisions: list[ExtractedItem] = Field(default_factory=list)
    risks: list[ExtractedItem] = Field(default_factory=list, description="Risks, obligations, penalties or open issues.")
    action_items: list[ExtractedItem] = Field(default_factory=list, description="Who must do what, by when, if stated.")


class Difference(BaseModel):
    topic: str
    in_a: Claim
    in_b: Claim


class CompareOut(BaseModel):
    overview: list[Claim] = Field(description="2-4 claims on how the documents relate overall.")
    similarities: list[Claim]
    differences: list[Difference]
    only_in_a: list[Claim]
    only_in_b: list[Claim]
