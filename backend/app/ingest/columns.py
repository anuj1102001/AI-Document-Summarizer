"""Reading order for multi-column pages.

PyMuPDF's sorted extraction reads strictly top-to-bottom, left-to-right, which interleaves the lines of side-by-side
columns ("Rohan Das   Work Experience" on one line). Here we look at individual text lines: if a clear vertical gutter
separates a left and a right group of lines that share vertical space, the page is read column by column instead.
"""

import pymupdf


def _lines(page: pymupdf.Page) -> list[tuple[float, float, float, float, str]]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                x0, y0, x1, y1 = line["bbox"]
                out.append((x0, y0, x1, y1, text))
    return out


def find_gutter(page: pymupdf.Page) -> float | None:
    """x position of a column gutter, or None for a single-column page."""
    lines = _lines(page)
    if len(lines) < 8:
        return None
    width = page.rect.width
    # Candidate gutters: x positions (in 2% steps across the middle of the page) that no line crosses.
    best = None
    for step in range(25, 76, 2):
        x = width * step / 100
        crossing = sum(1 for x0, _, x1, _, _ in lines if x0 < x - 2 and x1 > x + 2)
        left = [ln for ln in lines if ln[2] <= x + 2]
        right = [ln for ln in lines if ln[0] >= x - 2]
        if crossing > len(lines) * 0.05 or len(left) < 4 or len(right) < 4:
            continue
        # Both sides must have text in the same vertical band (otherwise it's just indentation).
        overlap = sum(1 for lt in left for rt in right if min(lt[3], rt[3]) - max(lt[1], rt[1]) > 1)
        if overlap >= 3 and (best is None or abs(x - width / 2) < abs(best - width / 2)):
            best = x
    return best


def column_text(page: pymupdf.Page, gutter: float) -> str:
    """Text read down the left column, then down the right one."""
    lines = _lines(page)
    left = sorted((ln for ln in lines if ln[2] <= gutter + 2), key=lambda ln: (round(ln[1]), ln[0]))
    right = sorted((ln for ln in lines if ln[0] >= gutter - 2 and ln[2] > gutter + 2), key=lambda ln: (round(ln[1]), ln[0]))
    full = sorted((ln for ln in lines if ln not in left and ln not in right), key=lambda ln: (round(ln[1]), ln[0]))

    def join(group) -> str:
        out, last_y = [], None
        for _x0, y0, _x1, y1, text in group:
            if last_y is not None and y0 - last_y > (y1 - y0) * 0.9:
                out.append("")  # a vertical gap: keep it as a paragraph break
            out.append(text)
            last_y = y1
        return "\n".join(out)

    return "\n\n".join(part for part in (join(full), join(left), join(right)) if part)
