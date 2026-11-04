"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  createExplanation,
  getMatch,
  getMatchState,
  getMoments,
  isPulseApiError,
  listMatches,
} from "@/lib/api";
import {
  formatKnowledgeReply,
  NEED_MATCH_COPY,
  resolveIntent,
  UNSUPPORTED_COPY,
} from "@/lib/companion-intent";
import {
  createConversationId,
  loadCompanionStore,
  saveCompanionStore,
  titleFromQuestion,
} from "@/lib/companion-storage";
import { sortMatches } from "@/lib/featured-match";
import { toAudienceLevel } from "@/lib/personalization";
import { useOnboarding } from "@/hooks/useOnboarding";
import type { AudienceLevel, MatchDetail, MatchState, MatchSummary, MomentView } from "@/types/api";
import type { ChatMessage, CompanionStore, Conversation } from "@/types/companion";

type CatalogStatus = "idle" | "loading" | "ready" | "empty" | "error";

type CompanionContextValue = {
  hydrated: boolean;
  conversations: Conversation[];
  active: Conversation | null;
  pending: boolean;
  catalogStatus: CatalogStatus;
  catalogError: string | null;
  matches: MatchSummary[];
  matchDetail: MatchDetail | null;
  matchState: MatchState | null;
  moments: MomentView[];
  momentsUnavailable: string | null;
  matchLoading: boolean;
  matchError: string | null;
  profileAudience: AudienceLevel;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  deleteConversation: (id: string) => void;
  clearAll: () => void;
  setAudienceLevel: (level: AudienceLevel) => void;
  setSelectedMatch: (matchId: string | null) => void;
  send: (text: string) => Promise<void>;
  retry: (retryText: string) => Promise<void>;
};

const CompanionContext = createContext<CompanionContextValue | null>(null);

function nowIso(): string {
  return new Date().toISOString();
}

function newConversation(audienceLevel: AudienceLevel): Conversation {
  const timestamp = nowIso();
  return {
    id: createConversationId(),
    title: "New conversation",
    createdAt: timestamp,
    updatedAt: timestamp,
    selectedMatchId: null,
    audienceLevel,
    messages: [],
  };
}

export function CompanionProvider({ children }: { children: ReactNode }) {
  const { state: profile, hydrated: profileHydrated } = useOnboarding();
  const profileAudience = toAudienceLevel(profile.selectedLevel);
  const [store, setStore] = useState<CompanionStore>({
    conversations: [],
    activeId: null,
  });
  const [hydrated, setHydrated] = useState(false);
  const [pending, setPending] = useState(false);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus>("idle");
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [matchDetail, setMatchDetail] = useState<MatchDetail | null>(null);
  const [matchState, setMatchState] = useState<MatchState | null>(null);
  const [moments, setMoments] = useState<MomentView[]>([]);
  const [momentsUnavailable, setMomentsUnavailable] = useState<string | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  useEffect(() => {
    if (!profileHydrated) {
      return;
    }
    const loaded = loadCompanionStore();
    if (loaded.conversations.length === 0) {
      const first = newConversation(profileAudience);
      setStore({ conversations: [first], activeId: first.id });
    } else {
      setStore(loaded);
    }
    setHydrated(true);
  }, [profileAudience, profileHydrated]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    saveCompanionStore(store);
  }, [hydrated, store]);

  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      setCatalogStatus("loading");
      try {
        const response = await listMatches();
        if (cancelled) {
          return;
        }
        const ordered = sortMatches(response.matches);
        setMatches(ordered);
        setCatalogStatus(ordered.length ? "ready" : "empty");
      } catch (error) {
        if (cancelled) {
          return;
        }
        setCatalogError(
          isPulseApiError(error)
            ? error.message
            : "Could not load the historical match catalog.",
        );
        setCatalogStatus("error");
      }
    }
    void loadCatalog();
    return () => {
      cancelled = true;
    };
  }, []);

  const active = useMemo(
    () => store.conversations.find((item) => item.id === store.activeId) ?? null,
    [store],
  );

  useEffect(() => {
    const matchId = active?.selectedMatchId;
    if (!matchId) {
      setMatchDetail(null);
      setMatchState(null);
      setMoments([]);
      setMomentsUnavailable(null);
      setMatchError(null);
      setMatchLoading(false);
      return;
    }
    const selectedId = matchId;
    let cancelled = false;
    async function loadMatch() {
      setMatchLoading(true);
      setMatchError(null);
      try {
        const [detail, stateResponse, momentsResponse] = await Promise.all([
          getMatch(selectedId),
          getMatchState(selectedId),
          getMoments(selectedId).catch(() => null),
        ]);
        if (cancelled) {
          return;
        }
        setMatchDetail(detail);
        setMatchState(stateResponse.state);
        if (momentsResponse?.available) {
          setMoments(momentsResponse.moments);
          setMomentsUnavailable(null);
        } else {
          setMoments([]);
          setMomentsUnavailable(
            momentsResponse?.unavailable_reason ?? "moments_unavailable",
          );
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setMatchError(
          isPulseApiError(error) ? error.message : "Could not load this historical match.",
        );
        setMatchDetail(null);
        setMatchState(null);
        setMoments([]);
      } finally {
        if (!cancelled) {
          setMatchLoading(false);
        }
      }
    }
    void loadMatch();
    return () => {
      cancelled = true;
    };
  }, [active?.selectedMatchId]);

  const patchActive = useCallback((updater: (current: Conversation) => Conversation) => {
    setStore((current) => {
      const id = current.activeId;
      if (!id) {
        return current;
      }
      return {
        ...current,
        conversations: current.conversations.map((item) =>
          item.id === id ? updater(item) : item,
        ),
      };
    });
  }, []);

  const newConversationHandler = useCallback(() => {
    setStore((current) => {
      const created = newConversation(profileAudience);
      return {
        conversations: [created, ...current.conversations],
        activeId: created.id,
      };
    });
  }, [profileAudience]);

  const selectConversation = useCallback((id: string) => {
    setStore((current) =>
      current.conversations.some((item) => item.id === id)
        ? { ...current, activeId: id }
        : current,
    );
  }, []);

  const renameConversation = useCallback((id: string, title: string) => {
    const nextTitle = title.trim() || "New conversation";
    setStore((current) => ({
      ...current,
      conversations: current.conversations.map((item) =>
        item.id === id ? { ...item, title: nextTitle, updatedAt: nowIso() } : item,
      ),
    }));
  }, []);

  const deleteConversation = useCallback((id: string) => {
    setStore((current) => {
      const remaining = current.conversations.filter((item) => item.id !== id);
      if (remaining.length === 0) {
        const created = newConversation(profileAudience);
        return { conversations: [created], activeId: created.id };
      }
      const activeId =
        current.activeId === id ? remaining[0].id : current.activeId;
      return { conversations: remaining, activeId };
    });
  }, [profileAudience]);

  const clearAll = useCallback(() => {
    const created = newConversation(profileAudience);
    setStore({ conversations: [created], activeId: created.id });
  }, [profileAudience]);

  const setAudienceLevel = useCallback(
    (level: AudienceLevel) => {
      patchActive((item) => ({ ...item, audienceLevel: level, updatedAt: nowIso() }));
    },
    [patchActive],
  );

  const setSelectedMatch = useCallback(
    (matchId: string | null) => {
      patchActive((item) => ({
        ...item,
        selectedMatchId: matchId,
        updatedAt: nowIso(),
      }));
    },
    [patchActive],
  );

  const send = useCallback(
    async (raw: string) => {
      const text = raw.replace(/\s+/g, " ").trim();
      if (!text || pending) {
        return;
      }
      const audience = active?.audienceLevel ?? profileAudience;
      const matchId = active?.selectedMatchId ?? null;
      const userMessage: ChatMessage = {
        id: createConversationId(),
        role: "user",
        content: text,
        createdAt: nowIso(),
      };
      patchActive((item) => ({
        ...item,
        title:
          item.messages.length === 0 ? titleFromQuestion(text) : item.title,
        updatedAt: nowIso(),
        messages: [...item.messages, userMessage],
      }));
      setPending(true);
      try {
        const assistant = await buildAssistantMessage({
          text,
          audience,
          matchId,
          latestSequence: matchDetail?.latest_sequence,
          moments,
        });
        patchActive((item) => ({
          ...item,
          updatedAt: nowIso(),
          messages: [...item.messages, assistant],
        }));
      } finally {
        setPending(false);
      }
    },
    [
      active?.audienceLevel,
      active?.selectedMatchId,
      matchDetail?.latest_sequence,
      moments,
      patchActive,
      pending,
      profileAudience,
    ],
  );

  const retry = useCallback(
    async (retryText: string) => {
      await send(retryText);
    },
    [send],
  );

  const value = useMemo(
    () => ({
      hydrated,
      conversations: store.conversations,
      active,
      pending,
      catalogStatus,
      catalogError,
      matches,
      matchDetail,
      matchState,
      moments,
      momentsUnavailable,
      matchLoading,
      matchError,
      profileAudience,
      newConversation: newConversationHandler,
      selectConversation,
      renameConversation,
      deleteConversation,
      clearAll,
      setAudienceLevel,
      setSelectedMatch,
      send,
      retry,
    }),
    [
      active,
      catalogError,
      catalogStatus,
      clearAll,
      deleteConversation,
      hydrated,
      matchDetail,
      matchError,
      matchLoading,
      matchState,
      matches,
      moments,
      momentsUnavailable,
      newConversationHandler,
      pending,
      profileAudience,
      renameConversation,
      retry,
      selectConversation,
      send,
      setAudienceLevel,
      setSelectedMatch,
      store.conversations,
    ],
  );

  return (
    <CompanionContext.Provider value={value}>{children}</CompanionContext.Provider>
  );
}

export function useCompanion() {
  const context = useContext(CompanionContext);
  if (!context) {
    throw new Error("useCompanion must be used within CompanionProvider");
  }
  return context;
}

async function buildAssistantMessage(input: {
  text: string;
  audience: AudienceLevel;
  matchId: string | null;
  latestSequence: number | undefined;
  moments: MomentView[];
}): Promise<ChatMessage> {
  const intent = resolveIntent(input.text, Boolean(input.matchId));
  const createdAt = nowIso();
  const id = createConversationId();

  if (intent.type === "knowledge") {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "knowledge",
      content: formatKnowledgeReply(intent.topic, input.audience),
    };
  }

  if (intent.type === "need_match") {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "need_match",
      content: NEED_MATCH_COPY,
    };
  }

  if (intent.type === "unsupported") {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "unsupported",
      content: UNSUPPORTED_COPY,
    };
  }

  if (!input.matchId) {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "need_match",
      content: NEED_MATCH_COPY,
    };
  }

  if (
    intent.sequence !== undefined &&
    (input.latestSequence === undefined ||
      intent.sequence < 0 ||
      intent.sequence > input.latestSequence)
  ) {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "unsupported",
      content: `Sequence ${intent.sequence} is not in the reconstructed file${
        input.latestSequence !== undefined
          ? ` (available 0–${input.latestSequence})`
          : ""
      }. PulseIQ will not invent a delivery.`,
      retryText: input.text,
    };
  }

  const sequence =
    intent.sequence ??
    (intent.preferMoment && input.moments[0]
      ? input.moments[0].sequence
      : undefined);

  try {
    const response = await createExplanation(input.matchId, input.audience, sequence);
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "match",
      content: response.summary,
      response,
    };
  } catch (error) {
    return {
      id,
      role: "assistant",
      createdAt,
      kind: "match",
      content: isPulseApiError(error)
        ? error.message
        : "The explanation service could not answer from this match context.",
      error: isPulseApiError(error) ? error.code : "request_failed",
      retryText: input.text,
    };
  }
}
