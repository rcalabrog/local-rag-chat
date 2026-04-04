"use client";

import { motion } from "framer-motion";

export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="inline-flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5 text-xs text-slate-300"
    >
      <span>Thinking</span>
      <span className="inline-flex">
        {[0, 1, 2].map((dot) => (
          <motion.span
            key={`dot-${dot}`}
            initial={{ opacity: 0.25, y: 0 }}
            animate={{ opacity: [0.25, 1, 0.25], y: [0, -1, 0] }}
            transition={{
              duration: 0.9,
              repeat: Number.POSITIVE_INFINITY,
              delay: dot * 0.15,
              ease: "easeInOut",
            }}
            className="mx-[1px]"
          >
            .
          </motion.span>
        ))}
      </span>
    </motion.div>
  );
}
