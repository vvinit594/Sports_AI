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
const GET_TIMEOUT_MS = 15_000;
const WRITE_TIMEOUT_MS = 35_000;

export class PulseApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detail: string | null = null,
    readonly requestId: string | null = null,
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
  const timeoutMs = method === "GET" || method === "HEAD" ? GET_TIMEOUT_MS : WRITE_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...init,
      cache: "no-store",
      method,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw new PulseApiError(
        504,
        "timeout",
        "The PulseIQ API timed out. Please try again.",
      );
    }
    throw new PulseApiError(
      0,
      "network_error",
      "Could not reach the PulseIQ API.",
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    let code = "request_failed";
    let message = `Request failed (${response.status})`;
    let detail: string | null = null;
    let requestId: string | null = null;
    try {
      const body = (await response.json()) as {
        error?: string;
        code?: string;
        detail?: string | null;
        request_id?: string | null;
      };
      code = body.code ?? code;
      message = body.error ?? message;
      detail = body.detail ?? null;
      requestId = body.request_id ?? null;
    } catch {
      // Non-JSON error bodies still surface the HTTP status.
    }
    if (code === "request_failed") {
      if (response.status === 504) {
        code = "timeout";
      } else if (response.status === 429) {
        code = "rate_limited";
      } else if (response.status === 502 || response.status === 503) {
        code = "provider_error";
      } else if (response.status === 401 || response.status === 403) {
        code = "invalid_credentials";
      }
    }
    throw new PulseApiError(response.status, code, message, detail, requestId);
  }

  return (await response.json()) as T;
}

function isAbortError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error as { name?: string }).name === "AbortError"
  );
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
