export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
  timestamp?: string;
  sources?: Source[];
};

export type Source = {
  text: string;
  filename: string;
  chunk_id: number;
};

export type ChatStreamEvent =
  | { type: "token"; content: string }
  | { type: "sources"; sources: Source[] }
  | { type: "done" }
  | { type: "error"; message: string };

export type ChatSessionSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatSession = ChatSessionSummary & {
  messages: ChatMessage[];
};
