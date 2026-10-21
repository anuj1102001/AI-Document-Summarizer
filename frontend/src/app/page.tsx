"use client";

import clsx from "clsx";
import { AlertTriangle, FileText, Loader2, Search, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Dropzone } from "@/components/dropzone";
import { api, describeError, type DocumentInfo, type SearchResult } from "@/lib/api";
import { checkFile, formatBytes, pageRef, timeAgo } from "@/lib/format";

const SAMPLES = [
  { file: "msa.pdf", name: "Master Services Agreement.pdf", title: "Services agreement", hint: "Fees, service levels, termination" },
  { file: "research.pdf", name: "Hybrid Work Field Study.pdf", title: "Research paper", hint: "A 12-month hybrid-work study" },
  { file: "policy.pdf", name: "Leave Travel and Expense Policy.pdf", title: "HR policy", hint: "Leave, travel and expenses" },
  { file: "minutes.pdf", name: "Steering Committee Minutes.pdf", title: "Meeting minutes", hint: "Decisions, risks, action items" },
];

type Notice = { tone: "error" | "info"; text: string };

export default function LibraryPage() {
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [uploading, setUploading] = useState<string[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(() => api.listDocuments().then(setDocs, (e) => setLoadError(describeError(e))), []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while anything is still being indexed.
  const processing = useMemo(() => docs?.some((d) => d.status === "processing"), [docs]);
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [processing, refresh]);

  async function uploadFiles(files: File[]) {
    const next: Notice[] = [];
    const ok = files.filter((f) => {
      const problem = checkFile(f);
      if (problem) next.push({ tone: "error", text: problem });
      return !problem;
    });
    setNotices(next);
    setUploading(ok.map((f) => f.name));
    for (const f of ok) {
      try {
        const r = await api.upload(f);
        if (r.duplicate) setNotices((n) => [...n, { tone: "info", text: `“${f.name}” is already in your library.` }]);
        if (r.document.empty_pages.length)
          setNotices((n) => [
            ...n,
            { tone: "info", text: `“${r.document.title}”: ${r.document.empty_pages.length} page(s) had no selectable text (possibly scanned) and were skipped.` },
          ]);
      } catch (e) {
        setNotices((n) => [...n, { tone: "error", text: `“${f.name}”: ${describeError(e)}` }]);
      }
      setUploading((u) => u.filter((name) => name !== f.name));
      refresh();
    }
  }

  async function loadSample(file: string, name: string) {
    const r = await fetch(`/samples/${file}`);
    const blob = await r.blob();
    uploadFiles([new File([blob], name, { type: "application/pdf" })]);
  }

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true);
    try {
      setResults(await api.search(query.trim()));
    } catch (err) {
      setNotices([{ tone: "error", text: describeError(err) }]);
    } finally {
      setSearching(false);
    }
  }

  async function remove(d: DocumentInfo) {
    if (!confirm(`Delete “${d.title}” and its analyses? This can't be undone.`)) return;
    await api.deleteDocument(d.id).catch((e) => setNotices([{ tone: "error", text: describeError(e) }]));
    refresh();
  }

  const empty = docs !== null && docs.length === 0 && uploading.length === 0;

  return (
    <div className="mx-auto max-w-[1080px] px-4 pb-24 pt-10 sm:px-6">
      {empty ? (
        <section className="mx-auto max-w-2xl pt-6 text-center animate-rise">
          <p className="eyebrow">Document intelligence</p>
          <h1 className="mt-3 font-serif text-[40px] font-semibold leading-[1.1] tracking-tight sm:text-[52px]">Read less. Understand more.</h1>
          <p className="mx-auto mt-4 max-w-xl text-[17px] leading-relaxed text-ink-2">
            Upload a contract, paper or report. Margin summarises it, answers your questions and pulls out the facts, and every claim comes with a quote you can check on
            the page.
          </p>
          <div className="mt-8 text-left">
            <Dropzone onFiles={uploadFiles} />
          </div>
          <div className="mt-8">
            <p className="eyebrow">Or try a sample</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {SAMPLES.map((s) => (
                <button key={s.file} onClick={() => loadSample(s.file, s.name)} className="card flex items-center gap-3 px-4 py-3 text-left transition-colors hover:border-ink-3">
                  <FileText className="h-5 w-5 shrink-0 text-ink-3" aria-hidden />
                  <span>
                    <span className="block text-sm font-medium">{s.title}</span>
                    <span className="block text-xs text-ink-3">{s.hint}</span>
                  </span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs text-ink-3">Samples are fictional documents written for testing.</p>
          </div>
        </section>
      ) : (
        <>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="font-serif text-[30px] font-semibold tracking-tight">Library</h1>
              <p className="mt-1 text-sm text-ink-2">Your documents stay private to this browser&apos;s workspace.</p>
            </div>
            <form onSubmit={runSearch} role="search" className="relative w-full sm:w-[380px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
              <input
                className="input pl-9 pr-9"
                placeholder="Search across all documents…"
                aria-label="Search across all documents"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (!e.target.value) setResults(null);
                }}
              />
              {searching && <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-ink-3" aria-label="Searching" />}
            </form>
          </div>

          {results && (
            <section aria-label="Search results" className="card mt-4 p-4 animate-rise">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">
                  {results.length ? `${results.length} passages match “${query}”` : `Nothing matches “${query}”.`}
                </p>
                <button className="btn-ghost h-8 px-2" onClick={() => (setResults(null), setQuery(""))} aria-label="Close search results">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <ul className="mt-2 divide-y divide-line">
                {results.map((r, i) => (
                  <li key={i}>
                    <Link href={`/d/${r.document_id}?page=${r.page}`} className="block rounded-md px-2 py-3 hover:bg-sunk">
                      <span className="text-xs text-ink-3">
                        {r.document_title} · {pageRef("Page", r.page)}
                        {r.heading ? ` · ${r.heading}` : ""}
                      </span>
                      <span className="mt-1 line-clamp-2 block font-serif text-[15px] text-ink-2">{r.snippet}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="mt-6">
            <Dropzone onFiles={uploadFiles} compact busy={uploading.length > 0} />
          </div>
        </>
      )}

      {notices.length > 0 && (
        <ul className="mx-auto mt-4 max-w-2xl space-y-2" aria-live="polite">
          {notices.map((n, i) => (
            <li key={i} className={clsx("flex items-start gap-2 rounded-lg px-3 py-2 text-sm", n.tone === "error" ? "bg-bad-soft text-bad" : "bg-sunk text-ink-2")}>
              {n.tone === "error" && <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
              {n.text}
            </li>
          ))}
        </ul>
      )}
      {loadError && <p className="mt-6 rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">{loadError}</p>}

      {!empty && (
        <section aria-label="Documents" className="mt-6">
          <ul className="card divide-y divide-line">
            {uploading.map((name) => (
              <li key={name} className="flex items-center gap-3 px-4 py-3.5">
                <Loader2 className="h-5 w-5 animate-spin text-ink-3" aria-hidden />
                <span className="text-sm">Uploading {name}…</span>
              </li>
            ))}
            {docs === null && !loadError
              ? [0, 1, 2].map((i) => (
                  <li key={i} className="flex items-center gap-3 px-4 py-4">
                    <div className="skeleton h-9 w-9" />
                    <div className="flex-1 space-y-2">
                      <div className="skeleton h-3.5 w-1/3" />
                      <div className="skeleton h-3 w-1/4" />
                    </div>
                  </li>
                ))
              : docs?.map((d) => <DocumentRow key={d.id} doc={d} onDelete={() => remove(d)} />)}
          </ul>
        </section>
      )}
    </div>
  );
}

function DocumentRow({ doc, onDelete }: { doc: DocumentInfo; onDelete: () => void }) {
  const ready = doc.status === "ready";
  const body = (
    <>
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-sunk font-mono text-2xs uppercase text-ink-2">{doc.kind === "text" ? "txt" : doc.kind}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-medium">{doc.title}</span>
        <span className="block text-xs text-ink-3">
          {doc.page_count} {doc.page_label.toLowerCase()}
          {doc.page_count === 1 ? "" : "s"} · {formatBytes(doc.size_bytes)} · added {timeAgo(doc.created_at)}
        </span>
      </span>
      {doc.status === "processing" && (
        <span className="inline-flex items-center gap-1.5 text-xs text-ink-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Indexing
        </span>
      )}
      {doc.status === "failed" && <span className="rounded-full bg-bad-soft px-2 py-0.5 text-xs text-bad">{doc.error ?? "Failed"}</span>}
    </>
  );
  return (
    <li className="group flex items-center">
      {ready ? (
        <Link href={`/d/${doc.id}`} className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3.5 hover:bg-sunk/60">
          {body}
        </Link>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3.5">{body}</div>
      )}
      <button onClick={onDelete} className="btn-ghost mr-2 h-8 px-2 opacity-60 group-hover:opacity-100" aria-label={`Delete ${doc.title}`}>
        <Trash2 className="h-4 w-4" />
      </button>
    </li>
  );
}
