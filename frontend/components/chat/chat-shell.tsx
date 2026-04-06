"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";

import type { ChatMessage, ChatSession, ChatSessionSummary, ChatStreamEvent, Source } from "@/lib/types";
import { ACTIVE_LLM } from "@/lib/llm-config";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SourcesPanel } from "@/components/chat/sources-panel";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { FileUpload } from "@/components/FileUpload";
import { UploadedFileBadge } from "@/components/UploadedFileBadge";
import { ConfirmModal } from "@/components/ConfirmModal";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ACTIVE_SESSION_STORAGE_KEY = "rag_active_session_id";

const emptySessionHint: ChatMessage = {
  role: "assistant",
  content: "Ask a question about your uploaded documents.",
};

function parseEventBlock(block: string): ChatStreamEvent | null {
  const dataLine = block
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("data:"));

  if (!dataLine) {
    return null;
  }

  const payload = dataLine.slice(5).trim();
  if (!payload) {
    return null;
  }

  try {
    return JSON.parse(payload) as ChatStreamEvent;
  } catch {
    return null;
  }
}

function summaryFromSession(session: ChatSession): ChatSessionSummary {
  return {
    id: session.id,
    title: session.title,
    created_at: session.created_at,
    updated_at: session.updated_at,
  };
}

function latestSourcesFromMessages(items: ChatMessage[]): Source[] {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const current = items[index];
    if (current.role === "assistant" && current.sources && current.sources.length > 0) {
      return current.sources;
    }
  }
  return [];
}

export function ChatShell() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadMessageType, setUploadMessageType] = useState<"success" | "error" | null>(null);
  const [activeDocuments, setActiveDocuments] = useState<string[]>([]);
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isClearingData, setIsClearingData] = useState(false);
  const [clearDataMessage, setClearDataMessage] = useState<string | null>(null);
  const [isSessionsLoading, setIsSessionsLoading] = useState(true);
  const [isSessionActionLoading, setIsSessionActionLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const pendingTokenRef = useRef("");
  const rafIdRef = useRef<number | null>(null);
  const uploadedFilename = activeDocuments.length > 0 ? activeDocuments[activeDocuments.length - 1] : null;

  const displayedMessages = messages.length > 0 ? messages : [emptySessionHint];
  const sidebarDisabled = isStreaming || isSessionActionLoading || isSessionsLoading;

  const fetchSessions = useCallback(async (): Promise<ChatSessionSummary[]> => {
    const response = await fetch(`${API_BASE_URL}/sessions`);
    if (!response.ok) {
      throw new Error("Failed to fetch sessions");
    }
    return (await response.json()) as ChatSessionSummary[];
  }, []);

  const createSession = useCallback(async (): Promise<ChatSession> => {
    const response = await fetch(`${API_BASE_URL}/sessions`, { method: "POST" });
    if (!response.ok) {
      throw new Error("Failed to create session");
    }
    return (await response.json()) as ChatSession;
  }, []);

  const storeActiveSessionId = useCallback((sessionId: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
    }
  }, []);

  const clearStoredSessionId = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    }
  }, []);

  const loadSessionById = useCallback(
    async (sessionId: string) => {
      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error("Failed to load session");
      }
      const session = (await response.json()) as ChatSession;
      setActiveSessionId(session.id);
      setMessages(session.messages);
      setSources(latestSourcesFromMessages(session.messages));
      storeActiveSessionId(session.id);
    },
    [storeActiveSessionId]
  );

  const refreshSessions = useCallback(async () => {
    const list = await fetchSessions();
    setSessions(list);
    return list;
  }, [fetchSessions]);

  const createAndActivateSession = useCallback(async (): Promise<string | null> => {
    const created = await createSession();
    const summary = summaryFromSession(created);
    setSessions((prev) => [summary, ...prev.filter((item) => item.id !== summary.id)]);
    setActiveSessionId(created.id);
    setMessages(created.messages);
    setSources([]);
    storeActiveSessionId(created.id);
    return created.id;
  }, [createSession, storeActiveSessionId]);

  useEffect(() => {
    let cancelled = false;

    const bootstrapSessions = async () => {
      setIsSessionsLoading(true);
      setError(null);

      try {
        let list = await fetchSessions();
        if (list.length === 0) {
          const created = await createSession();
          list = [summaryFromSession(created)];
        }

        if (cancelled) {
          return;
        }

        setSessions(list);
        const storedSessionId =
          typeof window !== "undefined" ? localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY) : null;
        const preferredSessionId =
          storedSessionId && list.some((item) => item.id === storedSessionId)
            ? storedSessionId
            : list[0]?.id ?? null;

        if (preferredSessionId) {
          await loadSessionById(preferredSessionId);
        } else {
          setActiveSessionId(null);
          setMessages([]);
          setSources([]);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load chat sessions.");
        }
      } finally {
        if (!cancelled) {
          setIsSessionsLoading(false);
        }
      }
    };

    void bootstrapSessions();

    return () => {
      cancelled = true;
    };
  }, [createSession, fetchSessions, loadSessionById]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isStreaming ? "auto" : "smooth" });
  }, [displayedMessages, isStreaming, sources.length, activeSessionId]);

  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  const canSend = useMemo(
    () => input.trim().length > 0 && !isStreaming && activeSessionId !== null,
    [input, isStreaming, activeSessionId]
  );

  const onUploadSuccess = (filename: string) => {
    setActiveDocuments((prev) => (prev.includes(filename) ? prev : [...prev, filename]));
    setUploadMessage("Document uploaded successfully");
    setUploadMessageType("success");
    setClearDataMessage(null);
  };

  const onUploadError = (message: string) => {
    setUploadMessage(message);
    setUploadMessageType("error");
  };

  const flushAssistantTokens = useCallback(() => {
    rafIdRef.current = null;
    const chunk = pendingTokenRef.current;
    if (!chunk) {
      return;
    }
    pendingTokenRef.current = "";
    setMessages((prev: ChatMessage[]) => {
      const last = prev[prev.length - 1];
      if (last && last.role === "assistant") {
        const updatedLast: ChatMessage = { ...last, content: `${last.content}${chunk}` };
        return [...prev.slice(0, -1), updatedLast];
      }
      return [...prev, { role: "assistant", content: chunk }];
    });
  }, []);

  const appendAssistantToken = useCallback(
    (token: string) => {
      pendingTokenRef.current += token;
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushAssistantTokens);
      }
    },
    [flushAssistantTokens]
  );

  const handleCreateSessionAction = useCallback(async () => {
    if (sidebarDisabled) {
      return;
    }

    setIsSessionActionLoading(true);
    setError(null);
    setSources([]);

    try {
      await createAndActivateSession();
    } catch {
      setError("Failed to create session.");
    } finally {
      setIsSessionActionLoading(false);
    }
  }, [createAndActivateSession, sidebarDisabled]);

  const handleSelectSessionAction = useCallback(
    async (sessionId: string) => {
      if (sidebarDisabled || sessionId === activeSessionId) {
        return;
      }

      setIsSessionActionLoading(true);
      setError(null);
      try {
        await loadSessionById(sessionId);
      } catch {
        setError("Failed to load selected session.");
      } finally {
        setIsSessionActionLoading(false);
      }
    },
    [activeSessionId, loadSessionById, sidebarDisabled]
  );

  const handleDeleteSessionAction = useCallback(
    async (sessionId: string) => {
      if (sidebarDisabled) {
        return;
      }

      setIsSessionActionLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { method: "DELETE" });
        if (!response.ok) {
          throw new Error("Failed to delete session");
        }

        let list = await refreshSessions();
        if (list.length === 0) {
          const created = await createSession();
          list = [summaryFromSession(created)];
          setSessions(list);
          setActiveSessionId(created.id);
          setMessages(created.messages);
          setSources([]);
          storeActiveSessionId(created.id);
          return;
        }

        if (activeSessionId === sessionId || !activeSessionId || !list.some((item) => item.id === activeSessionId)) {
          await loadSessionById(list[0].id);
        }
      } catch {
        setError("Failed to delete session.");
      } finally {
        setIsSessionActionLoading(false);
      }
    },
    [activeSessionId, createSession, loadSessionById, refreshSessions, sidebarDisabled, storeActiveSessionId]
  );

  const handleClearData = useCallback(async () => {
    setIsClearingData(true);
    setClearDataMessage(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to clear documents");
      }

      setInput("");
      setMessages([]);
      setSources([]);
      setUploadMessage(null);
      setUploadMessageType(null);
      setActiveDocuments([]);
      clearStoredSessionId();

      const created = await createSession();
      const summary = summaryFromSession(created);
      setSessions([summary]);
      setActiveSessionId(created.id);
      setMessages(created.messages);
      setSources([]);
      storeActiveSessionId(created.id);
      setClearDataMessage("All documents cleared");
    } catch {
      setClearDataMessage("Failed to clear documents");
    } finally {
      setIsClearingData(false);
      setIsClearModalOpen(false);
    }
  }, [clearStoredSessionId, createSession, storeActiveSessionId]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = input.trim();
    if (!question || isStreaming) {
      return;
    }

    let sessionId = activeSessionId;
    let startsFreshSession = false;
    if (!sessionId) {
      try {
        sessionId = await createAndActivateSession();
        startsFreshSession = true;
      } catch {
        setError("Unable to create a session.");
        return;
      }
      if (!sessionId) {
        setError("Unable to create a session.");
        return;
      }
    }

    setInput("");
    setError(null);
    setSources([]);
    setIsStreaming(true);
    setMessages((prev: ChatMessage[]) =>
      startsFreshSession
        ? [
            { role: "user", content: question },
            { role: "assistant", content: "" },
          ]
        : [
            ...prev,
            { role: "user", content: question },
            { role: "assistant", content: "" },
          ]
    );

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, active_documents: activeDocuments, session_id: sessionId }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Chat request failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          flushAssistantTokens();
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary).trim();
          buffer = buffer.slice(boundary + 2);
          boundary = buffer.indexOf("\n\n");

          if (!block) {
            continue;
          }

          const parsed = parseEventBlock(block);
          if (!parsed) {
            continue;
          }

          if (parsed.type === "token") {
            appendAssistantToken(parsed.content);
            continue;
          }

          if (parsed.type === "sources") {
            setSources(parsed.sources);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                next[next.length - 1] = { ...last, sources: parsed.sources };
              }
              return next;
            });
            continue;
          }

          if (parsed.type === "error") {
            setError(parsed.message);
          }
        }
      }
    } catch {
      flushAssistantTokens();
      setError("Unable to stream response from backend.");
      setMessages((prev: ChatMessage[]) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && last.content.trim() === "") {
          next[next.length - 1] = {
            role: "assistant",
            content: "I don't know",
          };
        }
        return next;
      });
    } finally {
      setIsStreaming(false);
      try {
        await refreshSessions();
      } catch {
        // Keep existing sidebar list when refresh fails.
      }
    }
  };

  return (
    <div className="flex h-screen w-full max-w-7xl flex-col gap-4 px-4 py-6 md:px-8">
      <div className="flex min-h-0 flex-1 flex-col gap-4 md:flex-row">
        <div className="h-56 md:h-full md:w-72 md:shrink-0">
          <ChatSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            disabled={sidebarDisabled}
            isLoading={isSessionsLoading}
            onCreateSessionAction={handleCreateSessionAction}
            onSelectSessionAction={handleSelectSessionAction}
            onDeleteSessionAction={handleDeleteSessionAction}
          />
        </div>

        <div className="flex min-h-0 flex-1 flex-col">
          <motion.header
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="mb-4 rounded-2xl border border-white/10 bg-panel/80 p-4 shadow-panel backdrop-blur"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <h1 className="text-lg font-semibold tracking-tight">Local RAG Chat</h1>
                <p className="truncate text-xs text-muted">{ACTIVE_LLM.label}</p>
              </div>
              <a
                href="https://github.com/rcalabrog/local-rag-chat"
                target="_blank"
                rel="noopener noreferrer"
                className="group shrink-0 rounded-xl border border-white/10 bg-white/5 p-2 transition hover:border-white/30 hover:bg-white/10"
                aria-label="Open project GitHub repository"
              >
                <Image
                  src="/images/rc_logo.png"
                  alt="RC logo"
                  width={110}
                  height={28}
                  priority
                  className="h-7 w-auto object-contain opacity-90 transition group-hover:opacity-100 md:h-8"
                />
              </a>
            </div>
          </motion.header>

          <div className="flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-panel/70 p-4 shadow-panel backdrop-blur">
            <div className="space-y-3">
              <AnimatePresence initial={false}>
                {displayedMessages.map((message, index) => (
                  <MessageBubble key={`${message.role}-${index}`} message={message} />
                ))}
              </AnimatePresence>

              <AnimatePresence>{isStreaming && <TypingIndicator />}</AnimatePresence>

              <SourcesPanel sources={sources} />

              <div ref={messagesEndRef} />
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-4">
            <AnimatePresence initial={false}>
              {uploadedFilename && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2 }}
                  className="mb-2"
                >
                  <UploadedFileBadge
                    filename={uploadedFilename}
                    onRemoveAction={() => setActiveDocuments((prev) => prev.slice(0, -1))}
                  />
                </motion.div>
              )}
            </AnimatePresence>
            {uploadMessage && (
              <motion.p
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className={`mb-2 text-xs ${
                  uploadMessageType === "success" ? "text-emerald-300" : "text-red-300"
                }`}
              >
                {uploadMessage}
              </motion.p>
            )}
            <div className="rounded-2xl border border-white/10 bg-panel p-2">
              <div className="flex items-center gap-2">
                <FileUpload
                  uploadUrl={`${API_BASE_URL}/upload`}
                  className="shrink-0"
                  disabled={isStreaming || isSessionActionLoading}
                  onUploadSuccessAction={onUploadSuccess}
                  onUploadErrorAction={onUploadError}
                />
                <input
                  value={input}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => setInput(event.target.value)}
                  disabled={isStreaming || activeSessionId === null}
                  placeholder="Ask about your documents..."
                  className="h-10 flex-1 rounded-xl bg-transparent px-3 text-sm text-white outline-none placeholder:text-muted disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!canSend}
                  className="h-10 rounded-xl bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-800"
                >
                  Send
                </button>
              </div>
            </div>
            {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
          </form>
        </div>
      </div>

      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-2">
        {clearDataMessage && (
          <p
            className={`rounded-lg px-3 py-1.5 text-xs ${
              clearDataMessage === "All documents cleared"
                ? "bg-emerald-500/20 text-emerald-300"
                : "bg-red-500/20 text-red-300"
            }`}
          >
            {clearDataMessage}
          </p>
        )}
        <button
          type="button"
          onClick={() => setIsClearModalOpen(true)}
          disabled={isClearingData || isStreaming}
          className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isClearingData ? "Clearing..." : "Clear Data"}
        </button>
      </div>

      <ConfirmModal
        isOpen={isClearModalOpen}
        title="Clear all indexed data"
        message="Are you sure you want to delete the uploaded documents?"
        confirmLabel="Confirm"
        cancelLabel="Cancel"
        isLoading={isClearingData}
        onConfirmAction={handleClearData}
        onCancelAction={() => {
          if (!isClearingData) {
            setIsClearModalOpen(false);
          }
        }}
      />
    </div>
  );
}
