import type { AudienceLevel } from "@/types/api";
import type { ChatMessage, CompanionStore, Conversation } from "@/types/companion";

export const COMPANION_STORAGE_KEY = "pulseiq.companion.v1";

const EMPTY_STORE: CompanionStore = {
  conversations: [],
  activeId: null,
};

const AUDIENCES: AudienceLevel[] = ["beginner", "casual", "advanced"];

export function loadCompanionStore(): CompanionStore {
  if (typeof window === "undefined") {
    return EMPTY_STORE;
  }
  try {
    const raw = window.localStorage.getItem(COMPANION_STORAGE_KEY);
    if (!raw) {
      return EMPTY_STORE;
    }
    return sanitizeStore(JSON.parse(raw));
  } catch {
    return EMPTY_STORE;
  }
}

export function saveCompanionStore(store: CompanionStore): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      COMPANION_STORAGE_KEY,
      JSON.stringify(sanitizeStore(store)),
    );
  } catch {
    // Quota / private-mode failures must not crash the companion.
  }
}

export function sanitizeStore(value: unknown): CompanionStore {
  if (!value || typeof value !== "object") {
    return EMPTY_STORE;
  }
  const record = value as Record<string, unknown>;
  const conversations = Array.isArray(record.conversations)
    ? record.conversations
        .map(sanitizeConversation)
        .filter((item): item is Conversation => item !== null)
    : [];
  const activeId =
    typeof record.activeId === "string" &&
    conversations.some((item) => item.id === record.activeId)
      ? record.activeId
      : (conversations[0]?.id ?? null);
  return { conversations, activeId };
}

export function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `c_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function titleFromQuestion(text: string): string {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return "New conversation";
  }
  return cleaned.length > 48 ? `${cleaned.slice(0, 45)}…` : cleaned;
}

function sanitizeConversation(value: unknown): Conversation | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (typeof record.id !== "string" || !record.id) {
    return null;
  }
  const createdAt = readIso(record.createdAt) ?? new Date().toISOString();
  const updatedAt = readIso(record.updatedAt) ?? createdAt;
  return {
    id: record.id,
    title:
      typeof record.title === "string" && record.title.trim()
        ? record.title.trim()
        : "New conversation",
    createdAt,
    updatedAt,
    selectedMatchId:
      typeof record.selectedMatchId === "string" && record.selectedMatchId
        ? record.selectedMatchId
        : null,
    audienceLevel: isAudience(record.audienceLevel)
      ? record.audienceLevel
      : "beginner",
    messages: Array.isArray(record.messages)
      ? record.messages
          .map(sanitizeMessage)
          .filter((item): item is ChatMessage => item !== null)
      : [],
  };
}

function sanitizeMessage(value: unknown): ChatMessage | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (record.role !== "user" && record.role !== "assistant") {
    return null;
  }
  if (typeof record.id !== "string" || typeof record.content !== "string") {
    return null;
  }
  const kind =
    record.kind === "knowledge" ||
    record.kind === "match" ||
    record.kind === "need_match" ||
    record.kind === "unsupported"
      ? record.kind
      : undefined;
  return {
    id: record.id,
    role: record.role,
    content: record.content,
    createdAt: readIso(record.createdAt) ?? new Date().toISOString(),
    kind,
    response: isExplanation(record.response) ? record.response : undefined,
    error: typeof record.error === "string" ? record.error : undefined,
    retryText: typeof record.retryText === "string" ? record.retryText : undefined,
  };
}

function isAudience(value: unknown): value is AudienceLevel {
  return typeof value === "string" && AUDIENCES.includes(value as AudienceLevel);
}

function readIso(value: unknown): string | null {
  if (typeof value !== "string" || !value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : value;
}

function isExplanation(value: unknown): value is ChatMessage["response"] {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.summary === "string" &&
    typeof record.what_happened === "string" &&
    typeof record.why_it_matters === "string" &&
    typeof record.source_match_id === "string"
  );
}
