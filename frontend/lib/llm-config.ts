export type LLMProvider = "local" | "openai";

export type LLMRuntimeConfig = {
  provider: LLMProvider;
  modelName: string;
  label: string;
};

const providerEnv = (process.env.NEXT_PUBLIC_LLM_PROVIDER ?? "local").toLowerCase();
const provider: LLMProvider = providerEnv === "openai" ? "openai" : "local";
const defaultModelName = provider === "openai" ? "gpt-4.1-mini" : "llama3.1:8b";
const modelName = process.env.NEXT_PUBLIC_LLM_MODEL ?? defaultModelName;
const labelPrefix = provider === "local" ? "Local LLM" : "Cloud LLM";

export const ACTIVE_LLM: LLMRuntimeConfig = {
  provider,
  modelName,
  label: `${labelPrefix}: ${modelName}`,
};
