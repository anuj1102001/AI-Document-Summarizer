/** The Margin mark: a page, its margin rule, and one highlighted line. */
export function LogoMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <rect x="3.5" y="2.5" width="17" height="19" rx="2.5" className="fill-surface stroke-ink" strokeWidth="1.5" />
      <path d="M8 3v18" className="stroke-accent" strokeWidth="1.5" />
      <rect x="10" y="8" width="8" height="2.6" rx="0.8" className="fill-mark" />
      <path d="M10.5 13.5h7M10.5 16.5h5" className="stroke-ink-3" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark />
      <span className="hidden font-serif text-[19px] font-semibold tracking-tight sm:inline">Margin</span>
    </span>
  );
}
