"use client";

import { ArrowLeftRight, Loader2, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { MetaLine } from "@/components/analysis-panel";
import { ClaimView, GroundingNote } from "@/components/claim";
import { DocProvider, useDoc } from "@/components/doc-context";
import { PageViewer } from "@/components/page-viewer";
import { api, describeError, type Analysis, type Claim, type CompareResult, type DocumentInfo } from "@/lib/api";

export default function ComparePage() {
  return (
    <Suspense>
      <CompareScreen />
    </Suspense>
  );
}

function CompareScreen() {
  const params = useSearchParams();
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [a, setA] = useState(params.get("a") ?? "");
  const [b, setB] = useState("");
  const [focus, setFocus] = useState("");
  const [result, setResult] = useState<Analysis<CompareResult> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then((d) => setDocs(d.filter((x) => x.status === "ready")), (e) => setError(describeError(e)));
  }, []);

  async function run(refresh = false) {
    if (!a || !b) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.compare(a, b, focus.trim() || null, refresh));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(false);
    }
  }

  const docA = docs?.find((d) => d.id === a);
  const docB = docs?.find((d) => d.id === b);

  return (
    <DocProvider docs={[docA, docB].filter(Boolean) as DocumentInfo[]}>
      <div className="mx-auto max-w-[1180px] px-4 pb-24 pt-10 sm:px-6">
        <h1 className="font-serif text-[30px] font-semibold tracking-tight">Compare documents</h1>
        <p className="mt-1 text-sm text-ink-2">Find what two versions, contracts or reports have in common and where they differ, with sources from each.</p>

        {docs && docs.length < 2 ? (
          <div className="card mt-6 px-5 py-8 text-center">
            <p className="font-medium">You need at least two documents to compare.</p>
            <Link href="/" className="btn-secondary mt-4">
              Go to the library
            </Link>
          </div>
        ) : (
          <form
            className="card mt-6 grid gap-3 p-4 md:grid-cols-[1fr_auto_1fr] md:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              run();
            }}
          >
            <DocSelect label="Document A" value={a} onChange={setA} docs={docs} exclude={b} />
            <ArrowLeftRight className="mx-auto mb-2.5 hidden h-4 w-4 text-ink-3 md:block" aria-hidden />
            <DocSelect label="Document B" value={b} onChange={setB} docs={docs} exclude={a} />
            <div className="md:col-span-3 md:flex md:items-end md:gap-3">
              <label className="block flex-1">
                <span className="mb-1 block text-xs font-medium text-ink-2">Focus (optional)</span>
                <input className="input" placeholder="e.g. payment terms and termination" value={focus} maxLength={300} onChange={(e) => setFocus(e.target.value)} />
              </label>
              <button type="submit" className="btn-primary mt-3 w-full md:mt-0 md:w-auto" disabled={!a || !b || busy}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Compare
              </button>
            </div>
          </form>
        )}

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
        {busy && !result && <p className="mt-8 text-sm text-ink-2" aria-live="polite">Reading both documents and lining up their terms…</p>}
        {result && docA && docB && <Results r={result} a={docA} b={docB} onRefresh={() => run(true)} refreshing={busy} />}
      </div>
      <SourceDrawer />
    </DocProvider>
  );
}

function DocSelect({ label, value, onChange, docs, exclude }: { label: string; value: string; onChange: (v: string) => void; docs: DocumentInfo[] | null; exclude: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink-2">{label}</span>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)} disabled={!docs}>
        <option value="">{docs ? "Choose a document…" : "Loading…"}</option>
        {docs?.map((d) => (
          <option key={d.id} value={d.id} disabled={d.id === exclude}>
            {d.title}
          </option>
        ))}
      </select>
    </label>
  );
}

function ClaimList({ claims, empty }: { claims: Claim[]; empty: string }) {
  if (!claims.length) return <p className="text-sm text-ink-3">{empty}</p>;
  return (
    <ul className="space-y-4">
      {claims.map((c, i) => (
        <li key={i}>
          <ClaimView claim={c} />
        </li>
      ))}
    </ul>
  );
}

function Results({ r: a, a: docA, b: docB, onRefresh, refreshing }: { r: Analysis<CompareResult>; a: DocumentInfo; b: DocumentInfo; onRefresh: () => void; refreshing: boolean }) {
  const r = a.result;
  return (
    <article className="mt-8 animate-rise">
      <GroundingNote g={r.grounding} />
      <section className="mt-6">
        <h2 className="eyebrow mb-3">Overview</h2>
        <ClaimList claims={r.overview} empty="No overview." />
      </section>

      <section className="mt-8">
        <h2 className="eyebrow mb-3">Differences · {r.differences.length}</h2>
        {r.differences.length === 0 ? (
          <p className="text-sm text-ink-3">No differences found in the passages compared.</p>
        ) : (
          <div className="overflow-hidden rounded-card border border-line">
            <div className="hidden grid-cols-[180px_1fr_1fr] gap-px bg-line text-xs font-medium text-ink-2 md:grid">
              <div className="bg-sunk px-3 py-2">Topic</div>
              <div className="truncate bg-sunk px-3 py-2">A · {docA.title}</div>
              <div className="truncate bg-sunk px-3 py-2">B · {docB.title}</div>
            </div>
            {r.differences.map((d, i) => (
              <div key={i} className="grid gap-px border-t border-line bg-line first:border-t-0 md:grid-cols-[180px_1fr_1fr]">
                <div className="bg-surface px-3 py-3 text-sm font-medium">{d.topic}</div>
                <div className="bg-surface px-3 py-3">
                  <p className="mb-1 font-mono text-2xs text-ink-3 md:hidden">A · {docA.title}</p>
                  <ClaimView claim={d.in_a} />
                </div>
                <div className="bg-surface px-3 py-3">
                  <p className="mb-1 font-mono text-2xs text-ink-3 md:hidden">B · {docB.title}</p>
                  <ClaimView claim={d.in_b} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="mt-8 grid gap-8 md:grid-cols-3">
        <section>
          <h2 className="eyebrow mb-3">In common</h2>
          <ClaimList claims={r.similarities} empty="Nothing notable in common." />
        </section>
        <section>
          <h2 className="eyebrow mb-3">Only in A</h2>
          <ClaimList claims={r.only_in_a} empty="Nothing found only in A." />
        </section>
        <section>
          <h2 className="eyebrow mb-3">Only in B</h2>
          <ClaimList claims={r.only_in_b} empty="Nothing found only in B." />
        </section>
      </div>
      <MetaLine meta={a.meta} onRefresh={onRefresh} refreshing={refreshing} />
    </article>
  );
}

/** Slide-over that shows the cited page with the quote highlighted, so you never lose your place in the comparison. */
function SourceDrawer() {
  const { focus, docs } = useDoc();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (focus) setOpen(true);
  }, [focus]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const doc = focus ? docs[focus.documentId] : undefined;
  if (!open || !doc) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/20" onClick={() => setOpen(false)}>
      <aside role="dialog" aria-modal="true" aria-label={`Source: ${doc.title}`} className="flex h-full w-full max-w-[640px] flex-col bg-paper shadow-lift animate-rise" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <p className="min-w-0 flex-1 truncate text-sm font-medium">{doc.title}</p>
          <button onClick={() => setOpen(false)} className="btn-ghost h-8 w-8 p-0" aria-label="Close source" autoFocus>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div data-scroll-root className="min-h-0 flex-1 overflow-y-auto bg-sunk/60 px-4 py-5">
          <PageViewer doc={doc} />
        </div>
      </aside>
    </div>
  );
}
