/**
 * Typed client for the Margin API. The browser holds a workspace token (created on first visit) and sends it as a
 * bearer token; the API scopes every request to that workspace.
 */

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "margin.workspace";

export type Support = "verified" | "approximate" | "unverified";

export type Citation = {
  quote: string;
  status: Support;
  document_id: string | null;
  page: number | null;
  chunk_id: string | null;
};

export type Claim = {
  text: string;
  kind: "stated" | "inferred";
  citations: Citation[];
  support: Support;
};

export type Grounding = {
  claims: number;
  verified?: number;
  approximate?: number;
  unverified?: number;
  stated_unverified?: number;
  grounded_rate: number | null;
};

export type DocumentInfo = {
  id: string;
  title: string;
  filename: string;
  kind: "pdf" | "docx" | "text";
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  error: string | null;
  page_count: number;
  char_count: number;
  empty_pages: number[];
  page_label: "Page" | "Part";
  created_at: number;
};

export type OutlineItem = { heading: string; page: number };

export type AnalysisMeta = {
  model: string;
  prompt_version: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  cached: boolean;
  created_at: number;
};

export type Analysis<T> = { id: string; kind: string; document_ids: string[]; input: unknown; result: T; meta: AnalysisMeta };

export type SummaryResult = {
  document_type: string;
  executive_summary: Claim[];
  key_takeaways: Claim[];
  sections: { heading: string; points: Claim[] }[];
  outline: OutlineItem[];
  strategy: string;
  grounding: Grounding;
};

export type AnswerResult = {
  status: "answered" | "partial" | "not_found";
  answer: Claim[];
  follow_ups: string[];
  retrieval: { label: string; document_id: string; page: number; heading: string | null; dense_rank: number | null; sparse_rank: number | null }[];
  grounding: Grounding;
};

export type ExtractedItem = { label: string; detail: string; kind: "stated" | "inferred"; citations: Citation[]; support: Support };

export type ExtractResult = {
  people_and_organisations: ExtractedItem[];
  dates_and_deadlines: ExtractedItem[];
  figures: ExtractedItem[];
  decisions: ExtractedItem[];
  risks: ExtractedItem[];
  action_items: ExtractedItem[];
  grounding: Grounding;
};

export type CompareResult = {
  overview: Claim[];
  similarities: Claim[];
  differences: { topic: string; in_a: Claim; in_b: Claim }[];
  only_in_a: Claim[];
  only_in_b: Claim[];
  grounding: Grounding;
};

export type SearchResult = { document_id: string; document_title: string; page: number; heading: string | null; snippet: string; score: number };

export type Health = { status: string; ai_configured: boolean; model: string | null; embedding_model: string };

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** Turn any failure into a message a person can act on. */
export function describeError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof TypeError) return "Can't reach the Margin server. Check your connection, or the server may be starting up (try again in ~30 seconds).";
  return "Something went wrong. Please try again.";
}

let tokenPromise: Promise<string> | null = null;

function storedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

async function token(): Promise<string> {
  const existing = storedToken();
  if (existing) return existing;
  tokenPromise ??= (async () => {
    const r = await fetch(`${API_URL}/api/workspaces`, { method: "POST" });
    if (!r.ok) throw new ApiError("WORKSPACE", "Couldn't create a workspace. Please refresh the page.", r.status);
    const { token } = (await r.json()) as { token: string };
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* private mode: the workspace lasts for this tab only */
    }
    return token;
  })();
  return tokenPromise;
}

export function resetWorkspace() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {}
  tokenPromise = null;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${await token()}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const r = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (r.status === 401 && retry) {
    // The server lost the workspace (e.g. a demo restart wiped its storage): start a fresh one.
    resetWorkspace();
    return request<T>(path, init, false);
  }
  if (r.status === 204) return undefined as T;
  const body = await r.json().catch(() => null);
  if (!r.ok) {
    const err = body?.error;
    throw new ApiError(err?.code ?? "HTTP_" + r.status, err?.message ?? `Request failed (${r.status}).`, r.status);
  }
  return body as T;
}

const json = (data: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(data) });

export const api = {
  health: () => fetch(`${API_URL}/api/health`).then((r) => r.json() as Promise<Health>),
  listDocuments: () => request<{ documents: DocumentInfo[] }>("/api/documents").then((r) => r.documents),
  getDocument: (id: string) => request<{ document: DocumentInfo; outline: OutlineItem[] }>(`/api/documents/${id}`),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ document: DocumentInfo; duplicate: boolean }>("/api/documents", { method: "POST", body: fd });
  },
  deleteDocument: (id: string) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  pageText: (id: string, page: number) => request<{ page: number; text: string }>(`/api/documents/${id}/pages/${page}`),
  pageImage: async (id: string, page: number): Promise<string> => {
    const r = await fetch(`${API_URL}/api/documents/${id}/pages/${page}/image`, { headers: { Authorization: `Bearer ${await token()}` } });
    if (!r.ok) throw new ApiError("PAGE", "Couldn't load this page.", r.status);
    return URL.createObjectURL(await r.blob());
  },
  locate: (id: string, page: number, q: string) =>
    request<{ rects: [number, number, number, number][] }>(`/api/documents/${id}/pages/${page}/locate?q=${encodeURIComponent(q.slice(0, 600))}`).then((r) => r.rects),
  search: (q: string) => request<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}`).then((r) => r.results),
  summary: (id: string, refresh = false) => request<Analysis<SummaryResult>>(`/api/documents/${id}/summary`, json({ refresh })),
  extract: (id: string, refresh = false) => request<Analysis<ExtractResult>>(`/api/documents/${id}/extract`, json({ refresh })),
  ask: (document_ids: string[], question: string, history: [string, string][]) => request<Analysis<AnswerResult>>("/api/ask", json({ document_ids, question, history })),
  compare: (document_a: string, document_b: string, focus: string | null, refresh = false) =>
    request<Analysis<CompareResult>>("/api/compare", json({ document_a, document_b, focus, refresh })),
  history: (document_id?: string) =>
    request<{ analyses: Analysis<unknown>[] }>(`/api/history${document_id ? `?document_id=${document_id}` : ""}`).then((r) => r.analyses),
};
