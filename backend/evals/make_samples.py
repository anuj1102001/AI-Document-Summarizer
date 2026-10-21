"""Write the evaluation corpus as PDFs into the frontend's public/samples, so visitors can try the app in one click.

Run from backend/:  python -m evals.make_samples
"""

from pathlib import Path

from evals.common import CORPUS, md_to_pdf

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for md in sorted(CORPUS.glob("*.md")):
        (OUT / f"{md.stem}.pdf").write_bytes(md_to_pdf(md.read_text(encoding="utf-8")))
        print("wrote", OUT / f"{md.stem}.pdf")


if __name__ == "__main__":
    main()
