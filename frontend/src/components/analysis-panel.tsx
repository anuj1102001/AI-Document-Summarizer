"use client";

import clsx from "clsx";
import { ArrowUp, ChevronDown, Loader2, RefreshCw, Search as SearchIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  api,
  describeError,
  type Analysis,
  type AnalysisMeta,
  type AnswerResult,
  type DocumentInfo,
  type ExtractedItem,
  type ExtractResult,
  type SummaryResult,
} from "@/lib/api";
import { CitationChip, ClaimView, GroundingNote } from "./claim";
import { useDoc } from "./doc-context";

type Tab = "summary" | "ask" | "facts";

export function AnalysisPanel({ doc }: { doc: DocumentInfo }) {
  const [tab, setTab] = useState<Tab>("summary");
  const tabs: { id: Tab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "ask", label: "Ask" },
    { id: "facts", label: "Key facts" },
  ];
  return (
    <div className="flex h-full flex-col">
      <div role="tablist" aria-label="Analysis" className="flex gap-1 border-b border-line px-4 pt-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setTab(t.id)}
            className={clsx("-mb-px border-b-2 px-3 pb-2.5 pt-1 text-sm transition-colors", tab === t.id ? "border-ink font-medium text-ink" : "border-transparent text-ink-3 hover:text-ink")}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="px-5 py-5">
          {tab === "summary" && <SummaryTab doc={doc} />}
          {tab === "ask" && <AskTab doc={doc} />}
          {tab === "facts" && <FactsTab doc={doc} />}
        </div>
      </div>
    </div>
  );
}

function useAnalysis<T>(run: (refresh: boolean) => Promise<Analysis<T>>, key: string) {
  const [data, setData] = useState<Analysis<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = (refresh = false) => {
    setLoading(true);
    setError(null);
    run(refresh)
      .then(setData, (e) => setError(describeError(e)))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return { data, error, loading, reload: () => load(true) };
}

export function MetaLine({ meta, onRefresh, refreshing }: { meta: AnalysisMeta; onRefresh?: () => void; refreshing?: boolean }) {
  return (
    <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line pt-3 font-mono text-2xs text-ink-3">
      <span>{meta.model}</span>
      <span>
        {(meta.input_tokens + meta.output_tokens).toLocaleString()} tokens · {(meta.latency_ms / 1000).toFixed(1)} s
      </span>
      {meta.cached && <span title="Saved from an earlier run: no new AI call, no cost.">cached</span>}
      {onRefresh && (
        <button onClick={onRefresh} disabled={refreshing} className="ml-auto inline-flex items-center gap-1 hover:text-ink disabled:opacity-50">
          <RefreshCw className={clsx("h-3 w-3", refreshing && "animate-spin")} aria-hidden /> Regenerate
        </button>
      )}
    </div>
  );
}

function Working({ lines }: { lines: string[] }) {
  return (
    <div aria-live="polite" aria-busy="true" className="space-y-4">
      <p className="flex items-center gap-2 text-sm text-ink-2">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        {lines[0]}
      </p>
      <div className="space-y-2.5">
        {[100, 92, 97, 60, 88, 75].map((w, i) => (
          <div key={i} className="skeleton h-3.5" style={{ width: `${w}%` }} />
        ))}
      </div>
      {lines[1] && <p className="text-xs text-ink-3">{lines[1]}</p>}
    </div>
  );
}

function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg bg-bad-soft px-4 py-3 text-sm text-bad">
      <p>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 font-medium underline underline-offset-2">
          Try again
        </button>
      )}
    </div>
  );
}

function Heading({ children }: { children: React.ReactNode }) {
  return <h3 className="eyebrow mb-3 mt-7 first:mt-0">{children}</h3>;
}

// ---- Summary --------------------------------------------------------------------------------------------------------

function SummaryTab({ doc }: { doc: DocumentInfo }) {
  const { data, error, loading, reload } = useAnalysis<SummaryResult>((refresh) => api.summary(doc.id, refresh), doc.id);
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data || (loading && !data)) return <Working lines={[`Reading ${doc.page_count} ${doc.page_label.toLowerCase()}s…`, "Long documents are summarised part by part, so this can take up to a minute."]} />;
  const r = data.result;
  return (
    <article className="animate-rise">
      <p className="eyebrow">{r.document_type}</p>
      <div className="mt-3">
        <GroundingNote g={r.grounding} />
      </div>
      <Heading>In brief</Heading>
      <ul className="space-y-4">
        {r.executive_summary.map((c, i) => (
          <li key={i}>
            <ClaimView claim={c} />
          </li>
        ))}
      </ul>
      <Heading>Key takeaways</Heading>
      <ul className="space-y-4">
        {r.key_takeaways.map((c, i) => (
          <li key={i} className="border-l-2 border-mark pl-3">
            <ClaimView claim={c} />
          </li>
        ))}
      </ul>
      <Heading>Section by section</Heading>
      <div className="space-y-2">
        {r.sections.map((s, i) => (
          <details key={i} className="group rounded-lg border border-line bg-surface" open={i === 0}>
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2.5 text-sm font-medium [&::-webkit-details-marker]:hidden">
              {s.heading}
              <ChevronDown className="h-4 w-4 text-ink-3 transition-transform group-open:rotate-180" aria-hidden />
            </summary>
            <ul className="space-y-3 border-t border-line px-3 py-3">
              {s.points.map((c, j) => (
                <li key={j}>
                  <ClaimView claim={c} />
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
      <MetaLine meta={data.meta} onRefresh={reload} refreshing={loading} />
      {r.strategy !== "single_pass" && <p className="mt-1 font-mono text-2xs text-ink-3">strategy: {r.strategy}</p>}
    </article>
  );
}

// ---- Ask ------------------------------------------------------------------------------------------------------------

type Turn = { question: string; result?: Analysis<AnswerResult>; error?: string };

const STARTERS = ["What is this document about, in two sentences?", "What dates or deadlines does it mention?", "What are the main risks or obligations?"];

function AskTab({ doc }: { doc: DocumentInfo }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Revisit earlier questions about this document.
    api.history(doc.id).then((all) => {
      const past = (all as Analysis<AnswerResult>[])
        .filter((a) => a.kind === "qa")
        .reverse()
        .map((a) => ({ question: (a.input as { question: string }).question, result: a }));
      setTurns(past);
    }, () => {});
  }, [doc.id]);

  useEffect(() => {
    // Braces matter: in current Chrome scrollIntoView() returns a Promise, which React would treat as a cleanup.
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, busy]);

  async function ask(q: string) {
    q = q.trim();
    if (q.length < 2 || busy) return;
    setQuestion("");
    setBusy(true);
    const history: [string, string][] = turns
      .filter((t) => t.result)
      .slice(-3)
      .flatMap((t) => [
        ["User", t.question],
        ["Assistant", t.result!.result.answer.map((c) => c.text).join(" ") || "(not found in the document)"],
      ]);
    setTurns((t) => [...t, { question: q }]);
    try {
      const result = await api.ask([doc.id], q, history);
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, result } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: describeError(e) } : x)));
    } finally {
      setBusy(false);
    }
  }

  const last = turns.at(-1)?.result?.result;
  const suggestions = last?.follow_ups?.length ? last.follow_ups : turns.length ? [] : STARTERS;

  return (
    <div className="flex min-h-full flex-col">
      {turns.length === 0 && (
        <div className="mb-5">
          <p className="font-serif text-lg">Ask anything about this document.</p>
          <p className="mt-1 text-sm text-ink-2">Answers come only from the document, with the passages they rely on. If it doesn&apos;t say, Margin will tell you.</p>
        </div>
      )}
      <ol className="space-y-6" aria-live="polite">
        {turns.map((t, i) => (
          <li key={i} className="animate-rise">
            <p className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-md bg-ink px-3.5 py-2 text-sm text-paper">{t.question}</p>
            <div className="mt-3">
              {t.error ? (
                <ErrorBox message={t.error} />
              ) : !t.result ? (
                <Working lines={["Searching the document and drafting an answer…"]} />
              ) : (
                <Answer a={t.result} />
              )}
            </div>
          </li>
        ))}
      </ol>
      <div ref={end} />
      <div className="sticky bottom-0 -mx-5 mt-6 border-t border-line bg-paper/95 px-5 pb-1 pt-3 backdrop-blur">
        {suggestions.length > 0 && !busy && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button key={s} onClick={() => ask(s)} className="rounded-full border border-line bg-surface px-2.5 py-1 text-left text-xs text-ink-2 hover:border-ink-3 hover:text-ink">
                {s}
              </button>
            ))}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          className="relative"
        >
          <label htmlFor="question" className="sr-only">
            Your question
          </label>
          <textarea
            id="question"
            rows={2}
            value={question}
            maxLength={1000}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(question);
              }
            }}
            placeholder="Ask a question…"
            className="input h-auto resize-none py-2.5 pr-12"
          />
          <button type="submit" disabled={busy || question.trim().length < 2} className="btn-primary absolute bottom-2 right-2 h-8 w-8 p-0" aria-label="Ask">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}

const STATUS_COPY = {
  answered: null,
  partial: "Only part of this is answered by the document.",
  not_found: "The document doesn't answer this.",
} as const;

function Answer({ a }: { a: Analysis<AnswerResult> }) {
  const r = a.result;
  const [trace, setTrace] = useState(false);
  const { docs } = useDoc();
  return (
    <div>
      {STATUS_COPY[r.status] && (
        <p className={clsx("mb-3 rounded-lg px-3 py-2 text-sm", r.status === "not_found" ? "bg-sunk text-ink-2" : "bg-warn-soft text-warn")}>{STATUS_COPY[r.status]}</p>
      )}
      <div className="space-y-3">
        {r.answer.map((c, i) => (
          <ClaimView key={i} claim={c} />
        ))}
      </div>
      {r.answer.length > 0 && (
        <div className="mt-3">
          <GroundingNote g={r.grounding} />
        </div>
      )}
      {r.retrieval?.length > 0 && (
        <div className="mt-3">
          <button onClick={() => setTrace((t) => !t)} className="inline-flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink" aria-expanded={trace}>
            <SearchIcon className="h-3 w-3" aria-hidden /> How this was found ({r.retrieval.length} passages)
            <ChevronDown className={clsx("h-3 w-3 transition-transform", trace && "rotate-180")} aria-hidden />
          </button>
          {trace && (
            <ul className="mt-2 space-y-1 rounded-lg bg-sunk p-2.5 font-mono text-2xs text-ink-2">
              {r.retrieval.map((p) => (
                <li key={p.label}>
                  {p.label} · {docs[p.document_id]?.page_label === "Part" ? "part" : "p."} {p.page}
                  {p.heading ? ` · ${p.heading}` : ""} — meaning #{p.dense_rank ?? "–"}, keywords #{p.sparse_rank ?? "–"}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <MetaLine meta={a.meta} />
    </div>
  );
}

// ---- Key facts ------------------------------------------------------------------------------------------------------

const CATEGORIES: { key: keyof Omit<ExtractResult, "grounding">; label: string }[] = [
  { key: "action_items", label: "Action items" },
  { key: "dates_and_deadlines", label: "Dates & deadlines" },
  { key: "figures", label: "Figures" },
  { key: "decisions", label: "Decisions" },
  { key: "risks", label: "Risks & obligations" },
  { key: "people_and_organisations", label: "People & organisations" },
];

function FactsTab({ doc }: { doc: DocumentInfo }) {
  const { data, error, loading, reload } = useAnalysis<ExtractResult>((refresh) => api.extract(doc.id, refresh), doc.id);
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return <Working lines={["Pulling out names, dates, figures, decisions and risks…"]} />;
  const r = data.result;
  return (
    <div className="animate-rise">
      <GroundingNote g={r.grounding} />
      {CATEGORIES.map(({ key, label }) => (
        <section key={key}>
          <Heading>
            {label} <span className="text-ink-3">· {r[key].length}</span>
          </Heading>
          {r[key].length === 0 ? (
            <p className="text-sm text-ink-3">None found in this document.</p>
          ) : (
            <ul className="divide-y divide-line rounded-lg border border-line bg-surface">
              {r[key].map((item, i) => (
                <FactRow key={i} item={item} />
              ))}
            </ul>
          )}
        </section>
      ))}
      <MetaLine meta={data.meta} onRefresh={reload} refreshing={loading} />
    </div>
  );
}

function FactRow({ item }: { item: ExtractedItem }) {
  return (
    <li className="px-3 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">{item.label}</p>
          <p className="text-sm text-ink-2">
            {item.kind === "inferred" && <span className="mr-1 text-2xs font-medium text-accent">Interpretation ·</span>}
            {item.detail}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-1">
          {item.citations.map((c, i) => (
            <CitationChip key={i} c={c} />
          ))}
        </div>
      </div>
    </li>
  );
}
