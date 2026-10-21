"use client";

import clsx from "clsx";
import { ArrowLeft, GitCompare, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AnalysisPanel } from "@/components/analysis-panel";
import { DocProvider, useDoc } from "@/components/doc-context";
import { PageViewer } from "@/components/page-viewer";
import { api, describeError, type DocumentInfo, type OutlineItem } from "@/lib/api";
import { formatBytes } from "@/lib/format";

export default function DocumentPage() {
  return (
    <Suspense>
      <DocumentScreen />
    </Suspense>
  );
}

function DocumentScreen() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentInfo | null>(null);
  const [outline, setOutline] = useState<OutlineItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const load = () =>
      api.getDocument(id).then(
        (r) => {
          setDoc(r.document);
          setOutline(r.outline);
          if (r.document.status === "processing") timer = setTimeout(load, 1500);
        },
        (e) => setError(describeError(e)),
      );
    load();
    return () => clearTimeout(timer);
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="font-serif text-2xl">This document isn&apos;t available.</p>
        <p className="mt-2 text-sm text-ink-2">{error}</p>
        <Link href="/" className="btn-secondary mt-6">
          Back to the library
        </Link>
      </div>
    );
  }
  if (!doc || doc.status === "processing") {
    return (
      <div className="grid place-items-center px-4 py-24 text-center" aria-live="polite">
        <Loader2 className="h-6 w-6 animate-spin text-ink-3" aria-hidden />
        <p className="mt-3 text-sm text-ink-2">{doc ? `Indexing “${doc.title}”…` : "Opening document…"}</p>
      </div>
    );
  }

  return (
    <DocProvider docs={[doc]}>
      <Workspace doc={doc} outline={outline} />
    </DocProvider>
  );
}

function Workspace({ doc, outline }: { doc: DocumentInfo; outline: OutlineItem[] }) {
  const { pane, setPane, goToPage } = useDoc();
  const params = useSearchParams();

  useEffect(() => {
    const p = Number(params.get("page"));
    if (p > 0) goToPage(doc.id, p);
  }, [params, doc.id, goToPage]);

  return (
    <div className="flex h-[calc(100dvh-56px)] flex-col">
      <div className="flex items-center gap-3 border-b border-line px-4 py-2.5 sm:px-6">
        <Link href="/" className="btn-ghost h-8 w-8 p-0" aria-label="Back to library">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-serif text-[17px] font-semibold">{doc.title}</h1>
          <p className="truncate text-xs text-ink-3">
            {doc.page_count} {doc.page_label.toLowerCase()}
            {doc.page_count === 1 ? "" : "s"} · {formatBytes(doc.size_bytes)} · {doc.filename}
          </p>
        </div>
        <Link href={`/compare?a=${doc.id}`} className="btn-secondary hidden sm:inline-flex">
          <GitCompare className="h-4 w-4" aria-hidden /> Compare
        </Link>
      </div>

      <div className="flex border-b border-line lg:hidden" role="tablist" aria-label="View">
        {(["document", "insights"] as const).map((p) => (
          <button key={p} role="tab" aria-selected={pane === p} onClick={() => setPane(p)} className={clsx("flex-1 py-2.5 text-sm capitalize", pane === p ? "border-b-2 border-ink font-medium" : "text-ink-3")}>
            {p}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[220px_minmax(0,1fr)_minmax(380px,460px)]">
        <aside className="hidden min-h-0 overflow-y-auto border-r border-line px-3 py-5 lg:block" aria-label="Outline">
          <p className="eyebrow px-2">Outline</p>
          {outline.length ? (
            <ul className="mt-2 space-y-0.5">
              {outline.map((o, i) => (
                <li key={i}>
                  <button onClick={() => goToPage(doc.id, o.page)} className="flex w-full items-baseline gap-2 rounded-md px-2 py-1.5 text-left text-sm text-ink-2 hover:bg-sunk hover:text-ink">
                    <span className="min-w-0 flex-1 truncate">{o.heading}</span>
                    <span className="font-mono text-2xs text-ink-3">{o.page}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 px-2 text-xs text-ink-3">No headings detected.</p>
          )}
        </aside>

        <section aria-label="Document" data-scroll-root className={clsx("min-h-0 overflow-y-auto bg-sunk/60 px-3 py-6 sm:px-8", pane === "insights" && "hidden lg:block")}>
          <div className="mx-auto max-w-[760px]">
            <PageViewer doc={doc} />
          </div>
        </section>

        <section aria-label="Insights" className={clsx("min-h-0 border-l border-line bg-paper", pane === "document" && "hidden lg:block")}>
          <AnalysisPanel doc={doc} />
        </section>
      </div>
    </div>
  );
}
