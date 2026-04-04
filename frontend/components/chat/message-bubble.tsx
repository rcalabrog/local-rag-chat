"use client";

import { motion } from "framer-motion";

import type { ChatMessage } from "@/lib/types";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={[
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 md:max-w-[70%]",
          isUser ? "bg-bubbleUser text-white" : "bg-bubbleAssistant text-slate-100",
        ].join(" ")}
      >
        {message.content || " "}
      </div>
    </motion.div>
  );
}
