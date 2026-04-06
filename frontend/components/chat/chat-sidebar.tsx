"use client";

import { motion } from "framer-motion";

import type { ChatSessionSummary } from "@/lib/types";

type ChatSidebarProps = {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  disabled?: boolean;
  isLoading?: boolean;
  onCreateSessionAction: () => void;
  onSelectSessionAction: (sessionId: string) => void;
  onDeleteSessionAction: (sessionId: string) => void;
};

function formatTitle(title: string): string {
  const trimmed = title.trim();
  return trimmed || "New Chat";
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  disabled = false,
  isLoading = false,
  onCreateSessionAction,
  onSelectSessionAction,
  onDeleteSessionAction,
}: ChatSidebarProps) {
  return (
    <aside className="h-full w-full border-r border-white/10 bg-slate-950/70 p-3 md:max-w-72 md:min-w-72">
      <button
        type="button"
        onClick={onCreateSessionAction}
        disabled={disabled || isLoading}
        className="mb-3 inline-flex w-full items-center justify-center rounded-xl border border-white/15 bg-slate-800/70 px-3 py-2 text-sm font-medium text-slate-100 transition hover:border-white/30 hover:bg-slate-700/70 disabled:cursor-not-allowed disabled:opacity-50"
      >
        + New Chat
      </button>

      <div className="h-[calc(100%-3.25rem)] space-y-1 overflow-y-auto pr-1">
        {isLoading && <p className="px-2 py-2 text-xs text-slate-400">Loading sessions...</p>}

        {!isLoading && sessions.length === 0 && <p className="px-2 py-2 text-xs text-slate-400">No sessions yet.</p>}

        {!isLoading &&
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <motion.div
                key={session.id}
                layout
                className={`group flex items-center gap-2 rounded-xl border px-2 py-1.5 transition ${
                  isActive
                    ? "border-blue-400/60 bg-blue-500/10"
                    : "border-transparent bg-transparent hover:border-white/10 hover:bg-white/5"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectSessionAction(session.id)}
                  disabled={disabled}
                  className="min-w-0 flex-1 text-left disabled:cursor-not-allowed"
                >
                  <p className="truncate text-sm text-slate-100">{formatTitle(session.title)}</p>
                </button>
                <button
                  type="button"
                  onClick={() => onDeleteSessionAction(session.id)}
                  disabled={disabled}
                  className="shrink-0 rounded-md px-1.5 py-0.5 text-xs text-slate-400 transition hover:bg-red-500/20 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Delete chat session"
                  title="Delete session"
                >
                  x
                </button>
              </motion.div>
            );
          })}
      </div>
    </aside>
  );
}
