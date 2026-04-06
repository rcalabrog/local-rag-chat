"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";

import type { ChatMessage, ChatStreamEvent, Source } from "@/lib/types";
import { ACTIVE_LLM } from "@/lib/llm-config";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SourcesPanel } from "@/components/chat/sources-panel";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { FileUpload } from "@/components/FileUpload";
import { UploadedFileBadge } from "@/components/UploadedFileBadge";
import { ConfirmModal } from "@/components/ConfirmModal";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const initialMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "Ask a question about your uploaded documents.",
  },
];

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

export function ChatShell() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
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
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const pendingTokenRef = useRef("");
  const rafIdRef = useRef<number | null>(null);
  const uploadedFilename = activeDocuments.length > 0 ? activeDocuments[activeDocuments.length - 1] : null;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isStreaming ? "auto" : "smooth" });
  }, [messages, isStreaming, sources.length]);

  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  const canSend = useMemo(() => input.trim().length > 0 && !isStreaming, [input, isStreaming]);

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

  const clearChatState = useCallback(() => {
    setMessages(initialMessages);
    setInput("");
    setSources([]);
    setError(null);
    setUploadMessage(null);
    setUploadMessageType(null);
    setActiveDocuments([]);
  }, []);

  const handleClearData = useCallback(async () => {
    setIsClearingData(true);
    setClearDataMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to clear documents");
      }

      clearChatState();
      setClearDataMessage("All documents cleared");
    } catch {
      setClearDataMessage("Failed to clear documents");
    } finally {
      setIsClearingData(false);
      setIsClearModalOpen(false);
    }
  }, [clearChatState]);

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = input.trim();
    if (!question || isStreaming) {
      return;
    }

    setInput("");
    setError(null);
    setSources([]);
    setIsStreaming(true);
    setMessages((prev: ChatMessage[]) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, active_documents: activeDocuments }),
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
    }
  };

  return (
    <div className="flex h-screen w-full max-w-5xl flex-col px-4 py-6 md:px-8">
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
            {messages.map((message, index) => (
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
              disabled={isStreaming}
              onUploadSuccessAction={onUploadSuccess}
              onUploadErrorAction={onUploadError}
            />
            <input
              value={input}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setInput(event.target.value)}
              disabled={isStreaming}
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
          disabled={isClearingData}
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
