"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import type { Source } from "@/lib/types";

type SourcesPanelProps = {
  sources: Source[];
};

function toPreview(text: string, maxLength: number = 200): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trimEnd()}...`;
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Record<number, boolean>>({});

  const hasSources = sources.length > 0;
  const sourceCountLabel = useMemo(() => `Sources (${sources.length})`, [sources.length]);

  if (!hasSources) {
    return null;
  }

  const toggleItem = (index: number) => {
    setExpandedItems((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-panel/75 p-3">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-lg px-1 py-1 text-left text-sm font-medium text-slate-100 transition hover:bg-white/5"
      >
        <span>{sourceCountLabel}</span>
        <motion.svg
          viewBox="0 0 20 20"
          className="h-4 w-4 text-slate-400"
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        >
          <path d="m5 7 5 6 5-6" />
        </motion.svg>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="sources-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 max-h-56 space-y-2 overflow-y-auto pr-1">
              {sources.map((source, index) => {
                const expanded = Boolean(expandedItems[index]);
                const preview = toPreview(source.text);
                const canExpand = source.text.length > preview.length;

                return (
                  <motion.div
                    key={`source-item-${source.filename}-${source.chunk_id}-${index}`}
                    className="rounded-xl border border-white/10 bg-slate-900/50 p-3 text-xs text-slate-300 transition hover:border-blue-400/40 hover:bg-slate-900/80"
                    whileHover={{ y: -1 }}
                    transition={{ duration: 0.15 }}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="flex items-center gap-1 truncate text-[11px] font-semibold uppercase tracking-wide text-slate-300">
                        <svg
                          viewBox="0 0 24 24"
                          className="h-3.5 w-3.5 shrink-0"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        >
                          <path d="M7 3h7l5 5v13H7z" />
                          <path d="M14 3v5h5" />
                        </svg>
                        <span className="truncate">{source.filename}</span>
                      </p>
                      <p className="shrink-0 text-[11px] text-slate-400">Chunk #{source.chunk_id}</p>
                    </div>
                    <p className="leading-5 text-slate-300">{expanded ? source.text : preview}</p>
                    {canExpand && (
                      <button
                        type="button"
                        onClick={() => toggleItem(index)}
                        className="mt-2 text-[11px] font-medium text-blue-300 transition hover:text-blue-200"
                      >
                        {expanded ? "Show less" : "Show more"}
                      </button>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
