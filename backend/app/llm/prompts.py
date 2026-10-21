"""Prompts, versioned. Bump PROMPT_VERSION whenever wording changes: cached analyses are keyed on it."""

PROMPT_VERSION = "2026-10-20.1"

GROUNDING_RULES = """Rules:
- Use only the passages provided. Never use outside knowledge, and never guess.
- Support every claim with at least one citation: the passage label and a short quote copied word for word from it.
- Mark a claim "stated" only if a passage says it directly. Anything you conclude, combine or interpret is "inferred".
- Keep numbers, names, dates and units exactly as written. Do not round or convert.
- Write plainly, in the document's language. No preamble."""

SYSTEM = (
    "You are Margin, a careful document analyst. You help people understand documents quickly without misrepresenting them.\n\n"
    + GROUNDING_RULES
)


def passages_block(passages: list[tuple[str, str, str]]) -> str:
    """passages: (label, location, text)."""
    return "\n\n".join(f"[{label}] ({loc})\n{text}" for label, loc, text in passages)


def summary_prompt(title: str, passages: list[tuple[str, str, str]]) -> str:
    return f"""Summarise the document "{title}".

Produce:
1. document_type.
2. executive_summary: the 3-5 things a busy reader must know first.
3. key_takeaways: 3-7 decision-relevant or actionable points.
4. sections: a detailed summary following the document's own structure, in order.

Passages (the full document, in order):
{passages_block(passages)}"""


def partial_summary_prompt(title: str, part: str, passages: list[tuple[str, str, str]]) -> str:
    return f"""This is {part} of the long document "{title}". List its most important points (at most 8), each with citations.

Passages:
{passages_block(passages)}"""


def reduce_summary_prompt(title: str, points: list[tuple[str, str, str]]) -> str:
    return f"""Below are verified points summarised from every part of the long document "{title}", labelled like passages.
Write the final summary from them. Cite the point labels, quoting the point text word for word.

{passages_block(points)}"""


def answer_prompt(question: str, passages: list[tuple[str, str, str]], history: list[tuple[str, str]]) -> str:
    convo = "\n".join(f"{role}: {text}" for role, text in history[-6:])
    return f"""Answer the question from the passages.
If the passages don't contain the answer, set status to not_found and say what is missing; do not answer from general knowledge.
If they only partly answer it, set status to partial and say which part is unsupported.

{f"Conversation so far:{chr(10)}{convo}{chr(10)}{chr(10)}" if convo else ""}Question: {question}

Passages (the most relevant parts of the document(s), not the whole text):
{passages_block(passages)}"""


def extract_prompt(title: str, passages: list[tuple[str, str, str]]) -> str:
    return f"""Extract the key facts from "{title}" into the categories. Only include items the passages actually contain; an empty
category is better than a guessed one. Each item needs a citation.

Passages:
{passages_block(passages)}"""


def compare_prompt(
    title_a: str, title_b: str, passages_a: list[tuple[str, str, str]], passages_b: list[tuple[str, str, str]], focus: str | None
) -> str:
    return f"""Compare document A ("{title_a}") with document B ("{title_b}").{f" Focus on: {focus}." if focus else ""}
Passages from A are labelled A1, A2...; passages from B are labelled B1, B2.... In a difference, in_a must cite A passages and in_b must cite B passages.
Only report a difference or an "only in" item when the passages show it; if a topic simply isn't covered in the passages you have, leave it out.

Document A passages:
{passages_block(passages_a)}

Document B passages:
{passages_block(passages_b)}"""
