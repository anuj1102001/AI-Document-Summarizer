"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { Citation, DocumentInfo } from "@/lib/api";

export type Focus = { documentId: string; page: number; quote: string; nonce: number };

type Ctx = {
  docs: Record<string, DocumentInfo>;
  focus: Focus | null;
  /** Scroll the viewer to a citation and highlight its quote. */
  show: (c: Citation) => void;
  goToPage: (documentId: string, page: number) => void;
  /** Mobile: which pane is visible. */
  pane: "document" | "insights";
  setPane: (p: "document" | "insights") => void;
};

const DocContext = createContext<Ctx | null>(null);

export function DocProvider({ docs, children }: { docs: DocumentInfo[]; children: React.ReactNode }) {
  const [focus, setFocus] = useState<Focus | null>(null);
  const [pane, setPane] = useState<"document" | "insights">("insights");

  const show = useCallback((c: Citation) => {
    if (!c.document_id || !c.page) return;
    setFocus({ documentId: c.document_id, page: c.page, quote: c.quote, nonce: Date.now() });
    setPane("document");
  }, []);

  const goToPage = useCallback((documentId: string, page: number) => {
    setFocus({ documentId, page, quote: "", nonce: Date.now() });
    setPane("document");
  }, []);

  const value = useMemo(() => ({ docs: Object.fromEntries(docs.map((d) => [d.id, d])), focus, show, goToPage, pane, setPane }), [docs, focus, show, goToPage, pane]);
  return <DocContext.Provider value={value}>{children}</DocContext.Provider>;
}

export function useDoc(): Ctx {
  const ctx = useContext(DocContext);
  if (!ctx) throw new Error("useDoc must be used inside DocProvider");
  return ctx;
}
