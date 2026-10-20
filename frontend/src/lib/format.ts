import type { Grounding, Support } from "./api";

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function timeAgo(epochSeconds: number, now = Date.now()): string {
  const s = Math.max(0, Math.round(now / 1000 - epochSeconds));
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  const d = Math.round(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export const SUPPORT_LABEL: Record<Support, string> = {
  verified: "Quote found in source",
  approximate: "Close match in source",
  unverified: "Not found in source",
};

export const SUPPORT_HELP: Record<Support, string> = {
  verified: "The quote behind this claim appears word for word in the document.",
  approximate: "Most of the quote's words appear together in the document, but not word for word. Check the highlighted passage.",
  unverified: "We couldn't find this quote in the document. Treat the claim with caution.",
};

/** One sentence that tells the reader how much of an AI result is backed by the document. */
export function groundingSentence(g: Grounding | undefined): string | null {
  if (!g || !g.claims) return null;
  const backed = (g.verified ?? 0) + (g.approximate ?? 0);
  const all = g.claims;
  if (backed === all) return `All ${all} ${all === 1 ? "claim is" : "claims are"} backed by quotes found in the document.`;
  const missing = all - backed;
  return `${backed} of ${all} claims are backed by quotes found in the document; ${missing} ${missing === 1 ? "isn't" : "aren't"}, so check ${missing === 1 ? "it" : "them"} before relying on ${missing === 1 ? "it" : "them"}.`;
}

export function pageRef(label: "Page" | "Part", page: number | null | undefined): string {
  if (!page) return "";
  return label === "Page" ? `p. ${page}` : `part ${page}`;
}

export const ACCEPTED_TYPES = [".pdf", ".docx", ".txt", ".md"];
export const MAX_UPLOAD_MB = 20;

/** Client-side check before uploading; the server validates again from the file's bytes. */
export function checkFile(file: { name: string; size: number }): string | null {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ACCEPTED_TYPES.includes(ext)) return `“${file.name}” isn't a supported type. Use PDF, Word (.docx), TXT or Markdown.`;
  if (file.size === 0) return `“${file.name}” is empty.`;
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `“${file.name}” is ${formatBytes(file.size)}; the limit is ${MAX_UPLOAD_MB} MB.`;
  return null;
}
