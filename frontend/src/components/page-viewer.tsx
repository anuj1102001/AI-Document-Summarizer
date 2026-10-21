"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { api, type DocumentInfo } from "@/lib/api";
import { useDoc } from "./doc-context";

/**
 * Continuous, lazily-loaded page view. PDFs show the real page (rendered server-side) with the cited quote highlighted
 * in place; Word and text files show their text parts with the quote marked.
 */
export function PageViewer({ doc }: { doc: DocumentInfo }) {
  const { focus } = useDoc();
  const pages = Array.from({ length: doc.page_count }, (_, i) => i + 1);
  const refs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!focus || focus.documentId !== doc.id) return;
    const el = refs.current[focus.page];
    // Scroll only the viewer's own panel, not the window (scrollIntoView would move every scrollable ancestor).
    const root = el?.closest<HTMLElement>("[data-scroll-root]");
    if (el && root) root.scrollTo({ top: el.getBoundingClientRect().top - root.getBoundingClientRect().top + root.scrollTop - 16, behavior: "smooth" });
  }, [focus, doc.id]);

  return (
    <div className="space-y-5">
      {pages.map((p) => (
        <div key={p} ref={(el) => void (refs.current[p] = el)} className="scroll-mt-4">
          {doc.kind === "pdf" ? <PdfPage doc={doc} page={p} /> : <TextPage doc={doc} page={p} />}
          <p className="mt-1.5 text-center font-mono text-2xs text-ink-3">
            {doc.page_label} {p} of {doc.page_count}
            {doc.empty_pages.includes(p) ? " · no selectable text" : ""}
          </p>
        </div>
      ))}
    </div>
  );
}

function useVisible<T extends Element>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || visible) return;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setVisible(true), { rootMargin: "800px 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, [visible]);
  return [ref, visible];
}

function PdfPage({ doc, page }: { doc: DocumentInfo; page: number }) {
  const { focus } = useDoc();
  const [ref, visible] = useVisible<HTMLDivElement>();
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [rects, setRects] = useState<[number, number, number, number][]>([]);
  const active = focus?.documentId === doc.id && focus.page === page;

  useEffect(() => {
    if (!visible || src) return;
    let url: string | null = null;
    api.pageImage(doc.id, page).then(
      (u) => setSrc((url = u)),
      () => setFailed(true),
    );
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, doc.id, page]);

  useEffect(() => {
    if (!active || !focus?.quote) {
      setRects([]);
      return;
    }
    api.locate(doc.id, page, focus.quote).then(setRects, () => setRects([]));
  }, [active, focus?.quote, focus?.nonce, doc.id, page]);

  return (
    <div ref={ref} className={clsx("relative mx-auto overflow-hidden rounded-sm bg-white shadow-page", active && "ring-2 ring-accent/50")} style={{ aspectRatio: "595 / 842" }}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={`${doc.title}, page ${page}`} className="h-full w-full" />
      ) : failed ? (
        <div className="grid h-full place-items-center text-sm text-ink-3">Couldn&apos;t load this page.</div>
      ) : (
        <div className="skeleton h-full w-full rounded-none" aria-label={`Loading page ${page}`} />
      )}
      {rects.map((r, i) => (
        <span
          key={`${focus?.nonce}-${i}`}
          className="pointer-events-none absolute rounded-[2px] bg-mark/45 mix-blend-multiply animate-rise"
          style={{ left: `${r[0] * 100}%`, top: `${r[1] * 100}%`, width: `${(r[2] - r[0]) * 100}%`, height: `${(r[3] - r[1]) * 100}%` }}
        />
      ))}
      {active && focus?.quote && rects.length === 0 && src && (
        <p className="absolute inset-x-3 bottom-3 rounded-md bg-surface/95 px-3 py-2 text-xs text-ink-2 shadow-lift">
          The quote is on this page but its layout (columns, line breaks) stopped us drawing an exact highlight.
        </p>
      )}
    </div>
  );
}

function TextPage({ doc, page }: { doc: DocumentInfo; page: number }) {
  const { focus } = useDoc();
  const [ref, visible] = useVisible<HTMLDivElement>();
  const [text, setText] = useState<string | null>(null);
  const active = focus?.documentId === doc.id && focus.page === page;

  useEffect(() => {
    if (visible && text === null) api.pageText(doc.id, page).then((r) => setText(r.text), () => setText(""));
  }, [visible, text, doc.id, page]);

  return (
    <div ref={ref} className={clsx("card min-h-[240px] px-6 py-5 sm:px-10 sm:py-8", active && "ring-2 ring-accent/50")}>
      {text === null ? (
        <div className="space-y-2">
          {[90, 100, 95, 70].map((w, i) => (
            <div key={i} className="skeleton h-3" style={{ width: `${w}%` }} />
          ))}
        </div>
      ) : (
        <div className="reading whitespace-pre-wrap text-[15px]">{active && focus?.quote ? <Marked text={text} quote={focus.quote} /> : text}</div>
      )}
    </div>
  );
}

/** Highlight the quote inside text, tolerant of whitespace differences. */
function Marked({ text, quote }: { text: string; quote: string }) {
  const words = quote.trim().split(/\s+/).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const m = words.length ? new RegExp(words.join("\\s+"), "i").exec(text) : null;
  if (!m) return <>{text}</>;
  return (
    <>
      {text.slice(0, m.index)}
      <mark className="rounded-sm bg-mark/60 px-0.5 text-ink">{m[0]}</mark>
      {text.slice(m.index + m[0].length)}
    </>
  );
}
