import type {
  AudienceLevel,
  ExplanationResponse,
  MatchDetail,
  MatchListResponse,
  MatchStateResponse,
  MomentsResponse,
  WinProbabilityResponse,
} from "@/types/api";
import {
  cacheKey,
  cachedGet,
  dedupeInflight,
  peekCached,
} from "@/lib/request-cache";

const API_PREFIX = "/api/v1";
const MATCHES_PATH = "/matches";

export class PulseApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detail: string | null = null,
  ) {
    super(message);
    this.name = "PulseApiError";
  }
}

export function isPulseApiError(error: unknown): error is PulseApiError {
  return error instanceof PulseApiError;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...init,
      cache: "no-store",
      method,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new PulseApiError(
      0,
      "network_error",
      "Could not reach the PulseIQ API.",
    );
  }

  if (!response.ok) {
    let code = "request_failed";
    let message = `Request failed (${response.status})`;
    let detail: string | null = null;
    try {
      const body = (await response.json()) as {
        error?: string;
        code?: string;
        detail?: string | null;
      };
      code = body.code ?? code;
      message = body.error ?? message;
      detail = body.detail ?? null;
    } catch {
      // Non-JSON error bodies still surface the HTTP status.
    }
    throw new PulseApiError(response.status, code, message, detail);
  }

  return (await response.json()) as T;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const body = typeof init?.body === "string" ? init.body : "";
  const key = cacheKey(method, path, body);
  const loader = () => apiRequest<T>(path, init);
  if (method === "GET") {
    return cachedGet(key, loader);
  }
  return dedupeInflight(key, loader);
}

export function peekCachedMatches(): MatchListResponse | undefined {
  return peekCached<MatchListResponse>(cacheKey("GET", MATCHES_PATH));
}

export function listMatches() {
  return apiFetch<MatchListResponse>(MATCHES_PATH);
}

export function getMatch(matchId: string) {
  return apiFetch<MatchDetail>(`/matches/${encodeURIComponent(matchId)}`);
}

export function getMatchState(
  matchId: string,
  sequence?: number,
  options?: { full?: boolean },
) {
  const params = new URLSearchParams();
  if (sequence !== undefined) {
    params.set("sequence", String(sequence));
  }
  if (options?.full) {
    params.set("full", "true");
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<MatchStateResponse>(
    `/matches/${encodeURIComponent(matchId)}/state${query}`,
  );
}

export function getWinProbability(matchId: string, sequence?: number) {
  const query =
    sequence === undefined ? "" : `?sequence=${encodeURIComponent(String(sequence))}`;
  return apiFetch<WinProbabilityResponse>(
    `/matches/${encodeURIComponent(matchId)}/win-probability${query}`,
  );
}

export function getMoments(matchId: string) {
  return apiFetch<MomentsResponse>(
    `/matches/${encodeURIComponent(matchId)}/moments`,
  );
}

export function createExplanation(
  matchId: string,
  audienceLevel: AudienceLevel,
  sequence?: number,
) {
  return apiFetch<ExplanationResponse>(
    `/matches/${encodeURIComponent(matchId)}/explanations`,
    {
      method: "POST",
      body: JSON.stringify({
        audience_level: audienceLevel,
        ...(sequence === undefined ? {} : { sequence }),
      }),
    },
  );
}
