"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Health } from "@/lib/api";
import { Logo } from "./logo";

const NAV = [
  { href: "/", label: "Library", match: (p: string) => p === "/" || p.startsWith("/d/") },
  { href: "/compare", label: "Compare", match: (p: string) => p.startsWith("/compare") },
  { href: "/case-study", label: "How it works", match: (p: string) => p.startsWith("/case-study") },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [health, setHealth] = useState<Health | null | "down">(null);

  useEffect(() => {
    api.health().then(setHealth, () => setHealth("down"));
  }, []);

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:gap-6 sm:px-6">
          <Link href="/" aria-label="Margin home">
            <Logo />
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={n.match(path) ? "page" : undefined}
                className={clsx("whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm transition-colors", n.match(path) ? "bg-sunk font-medium text-ink" : "text-ink-2 hover:text-ink")}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto">
            <AiStatus health={health} />
          </div>
        </div>
      </header>
      {health === "down" && (
        <div role="status" className="border-b border-warn/30 bg-warn-soft px-4 py-2 text-center text-sm text-warn">
          The Margin server isn&apos;t responding. On the free demo host it can take about 30 seconds to wake up; this page will work once it does.
        </div>
      )}
      {health && health !== "down" && health.model === "offline-demo" && (
        <div role="status" className="border-b border-warn/30 bg-warn-soft px-4 py-2 text-center text-sm text-warn">
          Offline demo mode: results below are sentences copied from your document by a simple rule, not AI. Connect a Gemini key for real summaries and answers.
        </div>
      )}
      {health && health !== "down" && !health.ai_configured && (
        <div role="status" className="border-b border-line bg-sunk px-4 py-2 text-center text-sm text-ink-2">
          AI is switched off on this server, so summaries and answers are unavailable. Uploading, reading and search still work.
        </div>
      )}
      <main id="main" className="flex-1">
        {children}
      </main>
    </div>
  );
}

function AiStatus({ health }: { health: Health | null | "down" }) {
  if (!health || health === "down") return null;
  return (
    <span className="hidden items-center gap-2 font-mono text-2xs text-ink-3 sm:inline-flex" title={`Answers by ${health.model ?? "—"}; search by ${health.embedding_model}`}>
      <span className={clsx("h-1.5 w-1.5 rounded-full", health.ai_configured ? "bg-ok" : "bg-ink-3")} />
      {health.ai_configured ? health.model : "AI off"}
    </span>
  );
}
