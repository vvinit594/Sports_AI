import type {
  AudienceLevel,
  ExplanationResponse,
  MatchDetail,
  MatchListResponse,
  MatchStateResponse,
  MomentsResponse,
  WinProbabilityResponse,
} from "@/types/api";

const API_PREFIX = "/api/v1";

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

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...init,
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
      "Could not reach the PulseIQ API. Start the FastAPI server on port 8000.",
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

export function listMatches() {
  return apiFetch<MatchListResponse>("/matches");
}

export function getMatch(matchId: string) {
  return apiFetch<MatchDetail>(`/matches/${encodeURIComponent(matchId)}`);
}

export function getMatchState(matchId: string, sequence?: number) {
  const query =
    sequence === undefined ? "" : `?sequence=${encodeURIComponent(String(sequence))}`;
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
