import type { AudienceLevel, ExplanationResponse } from "@/types/api";

export type ChatRole = "user" | "assistant";

export type AssistantKind = "knowledge" | "match" | "need_match" | "unsupported";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  kind?: AssistantKind;
  response?: ExplanationResponse;
  error?: string;
  retryText?: string;
};

export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  selectedMatchId: string | null;
  audienceLevel: AudienceLevel;
  messages: ChatMessage[];
};

export type CompanionStore = {
  conversations: Conversation[];
  activeId: string | null;
};
