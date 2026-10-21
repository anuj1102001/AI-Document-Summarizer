import Link from "next/link";

export const metadata = {
  title: "Case study",
  description: "How Margin turns a PDF summariser into a document tool you can check: grounded citations, hybrid retrieval, evaluation and design decisions.",
};

const V1_V2: [string, string, string][] = [
  ["Scope", "One endpoint: send the whole PDF's text to Gemini and return its summary", "Library, summaries, cited Q&A, key facts, comparison, search"],
  ["Trust", "Free text, no sources", "Every claim carries quotes; each quote is checked against the page and shown verified, approximate or not found"],
  ["Long documents", "Whole text in one prompt, however long", "Single pass up to ~180k characters, map-reduce above; questions use retrieval"],
  ["Retrieval", "None", "Local embeddings (bge-small) + BM25, fused with reciprocal rank fusion; measured in an eval"],
  ["Files", "PDF by filename; crashed on a missing folder", "PDF, DOCX, TXT, MD detected from bytes; encrypted, scanned and oversized files rejected with clear messages"],
  ["Security", "Uploaded filename used as a file path; a script printed the API key", "Server-generated file names, per-workspace bearer tokens, rate limiting, no internals in errors"],
  ["Reliability", "Crashed at start-up without a key; every error a 500", "Runs without a key (AI features say so); typed errors with stable codes; JSON logs with request ids"],
  ["Quality", "No tests; requirements file unreadable by pip", "42 backend tests, 9 frontend tests, CI, retrieval eval, Docker"],
  ["Interface", "Swagger UI only", "A reading workspace: real pages with the cited quote highlighted, on desktop and phone"],
];

const DECISIONS: [string, string][] = [
  [
    "Check every quote, don't just ask for citations",
    "Models cite the wrong passage or paraphrase while claiming to quote. After every call the server normalises each quote and looks for it in the cited passage, then in the rest of the document. The UI shows the result; a claim the model marked as stated but whose quote isn't found is counted and flagged.",
  ],
  [
    "Separate what the document says from what the AI thinks",
    "Every claim is labelled stated or interpretation. Summaries are allowed to synthesise, but the reader always knows which sentences they could find on the page.",
  ],
  [
    "Embeddings run locally",
    "bge-small through ONNX: about 130 MB of RAM, no key, no per-call cost, no document text sent anywhere just to index it, and the retrieval eval runs in CI. The trade-off is weaker multilingual and long-context recall than large hosted embedding models.",
  ],
  [
    "No vector database",
    "A question searches only the selected document's chunks: hundreds of vectors, a few milliseconds with NumPy. A vector DB would add a service to run without a measurable gain at this scale; the retrieval module is an interface so that can change.",
  ],
  [
    "Hybrid retrieval, kept honestly",
    "On this small eval set dense search alone ranked as well as or better than hybrid (see below). Hybrid is kept because BM25 catches identifiers and codes that embeddings blur, which this set covers thinly. The next step is a larger, identifier-heavy set to settle it, not tuning weights to 47 questions.",
  ],
  [
    "Whole document when it fits, retrieval when it doesn't",
    "Summaries and extraction read the whole document in one call up to ~180k characters (cheaper and more complete than retrieval for those tasks), and map-reduce beyond that, keeping only points whose quotes were verified. Questions always use retrieval, so they stay fast and cite precisely.",
  ],
  [
    "Cache by content, prompt version and model",
    "Re-opening a summary costs nothing. Bumping the prompt version invalidates old results automatically. Only real model calls count towards the hourly limit.",
  ],
  [
    "Accounts are a workspace token",
    "A visitor gets a random token kept in the browser; the server stores only its hash and scopes every query to it. No sign-up for a demo, but no recovery either. Real accounts would map users to workspaces.",
  ],
];

export default function CaseStudy() {
  return (
    <article className="mx-auto max-w-[760px] px-4 pb-24 pt-12 sm:px-6">
      <p className="eyebrow">Case study · AI engineering and product design</p>
      <h1 className="mt-3 font-serif text-[40px] font-semibold leading-[1.1] tracking-tight">Margin: a document assistant you can check</h1>
      <p className="mt-4 text-[17px] leading-relaxed text-ink-2">
        Margin started as a FastAPI endpoint that sent a PDF&apos;s text to Gemini and returned a summary. Version 2 rebuilds it around one idea: an AI summary is only
        useful if you can check it quickly. Every claim comes with a quote, every quote is verified against the page, and one click shows it highlighted on the real page.
      </p>
      <dl className="mt-8 grid grid-cols-2 gap-4 rounded-card border border-line bg-surface p-5 text-sm sm:grid-cols-4">
        {[
          ["Role", "Product, design and engineering"],
          ["Stack", "Python, FastAPI, Gemini, Next.js"],
          ["Retrieval", "bge-small + BM25 + RRF"],
          ["Status", "Working prototype; retrieval and answer evals run"],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="eyebrow">{k}</dt>
            <dd className="mt-1">{v}</dd>
          </div>
        ))}
      </dl>

      <Section n="01" title="The problem and who it's for">
        <p>
          Students, researchers, professionals and small teams spend hours reading contracts, papers, policies and minutes to find the few things that matter: what
          they owe, what was decided, what the evidence says. General chatbots can summarise, but their summaries are hard to trust. Checking a claim means hunting
          for it in the original, which can take as long as reading the document.
        </p>
        <Callout>
          <strong>Hypotheses, not findings.</strong> These users and pains come from desk research and my own use, not from interviews. The study plan in section 10
          is how I&apos;d test them.
        </Callout>
      </Section>

      <Section n="02" title="Vision and solution">
        <p>
          <strong>Read less, understand more, and check everything.</strong> Margin gives you a summary, answers and key facts, and keeps the source one click away. The
          design principle is that the evidence is part of the answer, not a footnote.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Executive summary, takeaways and a section-by-section summary, with a free outline from detected headings.</li>
          <li>Questions answered only from the document, with a clear &ldquo;the document doesn&apos;t say&rdquo; when it doesn&apos;t.</li>
          <li>Key facts in six categories: people and organisations, dates, figures, decisions, risks, action items.</li>
          <li>Comparison of two documents: in common, different, and only in one.</li>
          <li>A private library with search across every document.</li>
        </ul>
      </Section>

      <Section n="03" title="What v1 did, and what changed">
        <div className="overflow-x-auto rounded-card border border-line">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-sunk text-xs text-ink-2">
              <tr>
                <th className="px-3 py-2 font-medium" />
                <th className="px-3 py-2 font-medium">v1</th>
                <th className="px-3 py-2 font-medium">v2</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {V1_V2.map(([k, a, b]) => (
                <tr key={k} className="align-top">
                  <th className="px-3 py-2 font-medium">{k}</th>
                  <td className="px-3 py-2 text-ink-2">{a}</td>
                  <td className="px-3 py-2">{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-ink-3">The v1 issues were found by installing and running the original repository, not just reading it.</p>
      </Section>

      <Section n="04" title="Architecture and technical decisions">
        <Diagram />
        <div className="space-y-4">
          {DECISIONS.map(([t, b]) => (
            <div key={t}>
              <h3 className="font-medium">{t}</h3>
              <p className="mt-1 text-ink-2">{b}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section n="05" title="User journey and interface decisions">
        <ol className="list-decimal space-y-1 pl-5">
          <li>Drop a file, or try one of four sample documents. Upload errors explain what to do (&ldquo;this looks like a scanned PDF&rdquo;).</li>
          <li>The document opens as real pages beside the analysis; the outline jumps between sections.</li>
          <li>The summary arrives with a grounding note: &ldquo;All 23 claims are backed by quotes found in the document.&rdquo;</li>
          <li>Click any page chip: the viewer scrolls to the page and highlights the exact quote.</li>
          <li>Ask follow-up questions; open &ldquo;How this was found&rdquo; to see which passages were searched and how they ranked.</li>
        </ol>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Evidence colours mean one thing.</strong> Green: quote found word for word. Amber: close match. Red: not found. Interpretations carry a label instead
            of a colour.
          </li>
          <li>
            <strong>Reading type for reading.</strong> Source Serif for document text and AI prose, Plex Sans for interface, Plex Mono for metadata, one highlighter
            colour for evidence.
          </li>
          <li>
            <strong>Every state designed:</strong> empty library, indexing, loading, AI off, offline demo, server waking up, not found, partial answers.
          </li>
          <li>
            <strong>Accessible by default:</strong> skip link, real tabs with ARIA, keyboard-operable upload, visible focus, reduced-motion support, light and dark
            themes, a phone layout that switches between the document and its insights.
          </li>
          <li>
            <strong>Cost is visible:</strong> each result shows the model, tokens, time and whether it came from cache.
          </li>
        </ul>
      </Section>

      <Section n="06" title="RAG and evaluation">
        <p>
          The retrieval eval needs no API key and runs in CI. Four synthetic documents (15 pages, 47 chunks) and 47 answerable questions, each labelled with the page
          that holds the answer. A hit at k means a top-k passage covers that page. Run on 2026-10-21 with bge-small-en-v1.5:
        </p>
        <EvalTable
          caption="Scoped to the question's document (how Ask works)"
          rows={[
            ["Dense", "0.83", "0.957", "0.979", "0.892"],
            ["BM25", "0.681", "0.872", "0.936", "0.787"],
            ["Hybrid (RRF)", "0.787", "0.915", "1.0", "0.866"],
          ]}
        />
        <EvalTable
          caption="Across the whole library (four documents compete)"
          rows={[
            ["Dense", "0.809", "0.936", "0.979", "0.871"],
            ["BM25", "0.596", "0.745", "0.872", "0.695"],
            ["Hybrid (RRF)", "0.745", "0.894", "0.957", "0.83"],
          ]}
        />
        <p>
          <strong>What this says:</strong> on this set, dense search alone is as good as or better than hybrid; hybrid only wins at hit@6 within a document (the six
          passages Ask actually sends). Down-weighting BM25 closed the gap, but one question is 0.021 of any rate here, so I didn&apos;t tune to it. These documents
          and questions were written by the same person who built the pipeline, and a document-scoped search picks from about a dozen passages: treat this as a
          regression suite and a comparison, not real-world accuracy.
        </p>
        <p>
          <strong>Answer quality</strong> is measured by a second script (<code className="font-mono text-sm">evals/run_generation.py</code>): accuracy against
          expected facts, correct refusals on 7 unanswerable questions, false refusals, the share of claims whose quotes verify, stated-but-unverified claims,
          latency and tokens. It runs the real Ask pipeline end to end. Run on 2026-10-21 with gemini-3.5-flash-lite over 54 questions:
        </p>
        <EvalTable
          caption="Answer quality (47 answerable, 7 unanswerable questions)"
          head={["Metric", "Value"]}
          rows={[
            ["Answers containing every expected fact", "0.979 (46/47)"],
            ["Unanswerable questions correctly refused", "0.857 (6/7)"],
            ["Answerable questions wrongly refused", "0.0"],
            ["Claims whose quote verified in the source", "1.0"],
            ["Claims labelled “stated” that didn’t verify", "0"],
            ["Latency p50 / p95", "1.9 s / 14.5 s"],
            ["Tokens per question (mean)", "1,014"],
          ]}
        />
        <p>
          The one wrong answer was a real error: asked how long the first contract period is, it inferred &ldquo;at least twelve months&rdquo; from a termination
          clause and missed the stated 24 months, though it did mark the answer as partial. The failed refusal: asked what Neha Kulkarni reported about sales, it
          said (correctly, with a verified quote) that she sent apologies, instead of saying the minutes don&apos;t cover it. Accuracy is a strict string match against facts the
          builder wrote, on a small synthetic set, using the free tier, where a few responses took 10–15 seconds. Read it as evidence that grounding holds up, not
          as a benchmark.
        </p>
      </Section>

      <Section n="07" title="Challenges, iterations and trade-offs">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong>Two-column pages came out interleaved.</strong> Sorted text extraction reads straight across both columns. Margin now looks for a vertical gutter
            between groups of lines and reads each column top to bottom.
          </li>
          <li>
            <strong>Highlighting needs the page, not the text.</strong> Quotes are located on the rendered page with PyMuPDF and drawn as an overlay, so the
            highlight lands on what the reader actually sees. When a quote wraps strangely, the viewer says so instead of highlighting the wrong thing.
          </li>
          <li>
            <strong>Titles.</strong> Files named &ldquo;scan_0042.pdf&rdquo; became their title. Margin now prefers the PDF&apos;s metadata, then a meaningful
            filename, then the first heading.
          </li>
          <li>
            <strong>Working without a key.</strong> An offline demo mode copies sentences from the document so the whole interface can be built and tested without a
            key. It&apos;s labelled as not AI wherever it appears, and none of the portfolio images use it.
          </li>
        </ul>
      </Section>

      <Section n="08" title="Testing and verified results">
        <ul className="list-disc space-y-1 pl-5">
          <li>42 backend tests (pytest) with a fake model: parsing (including scanned, encrypted and two-column PDFs), chunking, quote verification, retrieval, workspace isolation, path traversal, upload limits, caching, map-reduce, rate limits and errors.</li>
          <li>9 frontend unit tests (Vitest), typecheck and lint.</li>
          <li>A scripted browser walkthrough of every screen at 1440 px and 390 px, in light and dark: no console errors, no horizontal scroll, skip link first in the tab order.</li>
          <li>CI runs lint, format, tests and the retrieval eval on every push.</li>
        </ul>
      </Section>

      <Section n="09" title="Demo">
        <p>
          Try it with one of the sample documents from the{" "}
          <Link href="/" className="underline underline-offset-2">
            library
          </Link>
          . The live demo runs gemini-3.5-flash-lite on free hosting, so the first visit after a quiet spell takes up to a minute to wake the server.
        </p>
      </Section>

      <Section n="10" title="What's next, and what I learned">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Usability study (planned, not done):</strong> 5-6 participants (students, an analyst, a paralegal) each answer 4 questions about a 20-page document,
            once with Margin and once with a plain PDF reader. Measure time to a correct answer, how often they click a citation, and confidence before and after. Key
            question: does the grounding note change how much people trust and check?
          </li>
          <li>Run the answer eval with Gemini and a second model; add an identifier-heavy retrieval set to settle hybrid vs dense.</li>
          <li>OCR for scanned PDFs, tables extracted as tables, and accounts with sharing for teams.</li>
          <li>
            <strong>Lesson:</strong> &ldquo;add citations&rdquo; isn&apos;t a feature until something checks them. The verification step and the UI that shows its
            result are what make the product trustworthy, more than the model choice.
          </li>
        </ul>
      </Section>
    </article>
  );
}

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-14">
      <p className="font-mono text-2xs text-ink-3">{n}</p>
      <h2 className="mt-1 font-serif text-[26px] font-semibold tracking-tight">{title}</h2>
      <div className="mt-4 space-y-4 text-[16px] leading-relaxed">{children}</div>
    </section>
  );
}

function Callout({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border-l-4 border-mark bg-sunk px-4 py-3 text-sm text-ink-2">{children}</p>;
}

function EvalTable({ caption, rows, head = ["Mode", "hit@1", "hit@3", "hit@6", "MRR"] }: { caption: string; rows: string[][]; head?: string[] }) {
  return (
    <div className="overflow-x-auto rounded-card border border-line">
      <table className="w-full min-w-[420px] text-right text-sm">
        <caption className="bg-sunk px-3 py-2 text-left text-xs font-medium text-ink-2">{caption}</caption>
        <thead className="text-xs text-ink-3">
          <tr>
            {head.map((h, i) => (
              <th key={h} className={i ? "px-3 py-2 font-medium" : "px-3 py-2 text-left font-medium"}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-surface font-mono">
          {rows.map((r) => (
            <tr key={r[0]}>
              {r.map((c, i) => (
                <td key={i} className={i ? "px-3 py-2" : "px-3 py-2 text-left font-sans"}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Diagram() {
  const box = "rounded-lg border border-line bg-surface px-3 py-2 text-center text-xs";
  const arrow = <span className="text-center text-ink-3" aria-hidden>↓</span>;
  return (
    <figure className="rounded-card border border-line bg-sunk/60 p-4" aria-label="Architecture diagram">
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <p className="eyebrow">Indexing (once per upload)</p>
          <div className={box}>Upload · type detected from bytes · limits</div>
          {arrow}
          <div className={box}>PyMuPDF / python-docx · per-page text · column-aware · scanned-page detection</div>
          {arrow}
          <div className={box}>Page-aware chunks with headings</div>
          {arrow}
          <div className={box}>bge-small embeddings (local) → SQLite</div>
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="eyebrow">Answering (each request)</p>
          <div className={box}>Question · summary · extraction · comparison</div>
          {arrow}
          <div className={box}>Dense + BM25 → reciprocal rank fusion (or whole document when it fits)</div>
          {arrow}
          <div className={box}>Gemini · structured output · labelled passages</div>
          {arrow}
          <div className={box}>Quote verification → pages → cache → UI highlight</div>
        </div>
      </div>
      <figcaption className="mt-3 text-xs text-ink-3">FastAPI backend (Docker), Next.js frontend. Workspace token on every request; per-workspace hourly AI limit.</figcaption>
    </figure>
  );
}
