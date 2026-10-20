"use client";

import clsx from "clsx";
import { CircleAlert, CircleCheck, CircleDashed } from "lucide-react";
import type { Citation, Claim, Grounding, Support } from "@/lib/api";
import { groundingSentence, SUPPORT_HELP, SUPPORT_LABEL } from "@/lib/format";
import { useDoc } from "./doc-context";

const SUPPORT_STYLE: Record<Support, string> = {
  verified: "text-ok",
  approximate: "text-warn",
  unverified: "text-bad",
};

export function SupportIcon({ support, className = "h-3.5 w-3.5" }: { support: Support; className?: string }) {
  const Icon = support === "verified" ? CircleCheck : support === "approximate" ? CircleDashed : CircleAlert;
  return <Icon className={clsx(className, SUPPORT_STYLE[support])} aria-label={SUPPORT_LABEL[support]} />;
}

/** A source chip: page reference, colored by whether its quote was found. Clicking shows the quote on the page. */
export function CitationChip({ c }: { c: Citation }) {
  const { docs, show } = useDoc();
  const doc = c.document_id ? docs[c.document_id] : undefined;
  const label = doc?.page_label === "Part" ? `part ${c.page}` : `p. ${c.page}`;
  const multiDoc = Object.keys(docs).length > 1;
  if (!c.page || !doc) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-bad-soft px-1.5 py-0.5 font-mono text-2xs text-bad" title={`“${c.quote}” — ${SUPPORT_HELP.unverified}`}>
        <SupportIcon support="unverified" className="h-3 w-3" /> source?
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={() => show(c)}
      title={`“${c.quote}”\n${SUPPORT_HELP[c.status]}`}
      aria-label={`Show source: ${multiDoc ? doc.title + ", " : ""}${label}. ${SUPPORT_LABEL[c.status]}.`}
      className={clsx(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-2xs transition-colors",
        c.status === "verified" && "border-ok/25 bg-ok-soft text-ok hover:border-ok/60",
        c.status === "approximate" && "border-warn/25 bg-warn-soft text-warn hover:border-warn/60",
        c.status === "unverified" && "border-bad/25 bg-bad-soft text-bad hover:border-bad/60",
      )}
    >
      <SupportIcon support={c.status} className="h-3 w-3" />
      {multiDoc ? `${doc.title.slice(0, 18)}${doc.title.length > 18 ? "…" : ""} · ` : ""}
      {label}
    </button>
  );
}

/** One claim: the text, whether the document states it or the AI inferred it, and its sources. */
export function ClaimView({ claim, className }: { claim: Claim; className?: string }) {
  const inferred = claim.kind === "inferred";
  const shaky = claim.support === "unverified";
  return (
    <div className={clsx("group", className)}>
      <p className={clsx("reading text-[15.5px]", shaky && "text-ink-2")}>
        {inferred && (
          <span className="mr-1.5 inline-block -translate-y-px rounded bg-accent-soft px-1.5 py-px align-middle font-sans text-2xs font-medium text-accent" title="The AI's interpretation, not a statement the document makes directly.">
            Interpretation
          </span>
        )}
        {claim.text}
      </p>
      {claim.citations.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {claim.citations.map((c, i) => (
            <CitationChip key={i} c={c} />
          ))}
        </div>
      )}
      {shaky && <p className="mt-1 text-xs text-bad">We couldn&apos;t find this in the document. Check it before relying on it.</p>}
    </div>
  );
}

export function GroundingNote({ g }: { g?: Grounding }) {
  const sentence = groundingSentence(g);
  if (!sentence || !g) return null;
  const full = (g.verified ?? 0) + (g.approximate ?? 0) === g.claims;
  return (
    <p className={clsx("flex items-start gap-2 rounded-lg px-3 py-2 text-xs", full ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn")} role="note">
      <SupportIcon support={full ? "verified" : "approximate"} className="mt-px h-3.5 w-3.5 shrink-0" />
      {sentence}
    </p>
  );
}
