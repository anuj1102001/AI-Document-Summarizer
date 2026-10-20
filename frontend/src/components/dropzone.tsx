"use client";

import clsx from "clsx";
import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { ACCEPTED_TYPES, MAX_UPLOAD_MB } from "@/lib/format";

/** Drag-and-drop or click (or Enter/Space) to choose files. Accessible as a button. */
export function Dropzone({ onFiles, compact, busy }: { onFiles: (files: File[]) => void; compact?: boolean; busy?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload documents"
      aria-busy={busy}
      onClick={() => input.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          input.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (e.dataTransfer.files.length) onFiles(Array.from(e.dataTransfer.files));
      }}
      className={clsx(
        "group flex cursor-pointer flex-col items-center justify-center rounded-card border-2 border-dashed text-center transition-colors",
        compact ? "gap-1 px-4 py-5" : "gap-3 px-6 py-12",
        over ? "border-accent bg-accent-soft" : "border-line bg-surface hover:border-ink-3",
      )}
    >
      <UploadCloud className={clsx("text-ink-3 transition-colors group-hover:text-accent", compact ? "h-5 w-5" : "h-8 w-8")} aria-hidden />
      <p className={clsx("font-medium", compact ? "text-sm" : "text-base")}>{over ? "Drop to upload" : "Drop files here, or click to choose"}</p>
      <p className="text-xs text-ink-3">
        PDF, Word, TXT or Markdown · up to {MAX_UPLOAD_MB} MB · text-based PDFs (scans aren&apos;t supported yet)
      </p>
      <input
        ref={input}
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) onFiles(Array.from(e.target.files));
          e.target.value = "";
        }}
      />
    </div>
  );
}
