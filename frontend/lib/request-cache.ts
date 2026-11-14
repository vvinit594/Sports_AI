const GET_TTL_MS = 5 * 60 * 1000;

type CacheEntry = {
  value: unknown;
  expires: number;
};

const memory = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<unknown>>();

export const TRENDING_MOMENT_CONCURRENCY = 3;

export function cacheKey(method: string, path: string, body = ""): string {
  return `${method}:${path}:${body}`;
}

export function peekCached<T>(key: string): T | undefined {
  const hit = memory.get(key);
  if (!hit) {
    return undefined;
  }
  if (hit.expires <= Date.now()) {
    memory.delete(key);
    return undefined;
  }
  return hit.value as T;
}

export async function cachedGet<T>(
  key: string,
  loader: () => Promise<T>,
  ttlMs = GET_TTL_MS,
): Promise<T> {
  const cached = peekCached<T>(key);
  if (cached !== undefined) {
    return cached;
  }

  const pending = inflight.get(key);
  if (pending) {
    return pending as Promise<T>;
  }

  const request = loader().then(
    (value) => {
      if (inflight.get(key) === request) {
        inflight.delete(key);
      }
      memory.set(key, { value, expires: Date.now() + ttlMs });
      return value;
    },
    (error: unknown) => {
      if (inflight.get(key) === request) {
        inflight.delete(key);
      }
      memory.delete(key);
      throw error;
    },
  );

  inflight.set(key, request);
  return request;
}

export async function dedupeInflight<T>(
  key: string,
  loader: () => Promise<T>,
): Promise<T> {
  const pending = inflight.get(key);
  if (pending) {
    return pending as Promise<T>;
  }

  const request = loader().then(
    (value) => {
      if (inflight.get(key) === request) {
        inflight.delete(key);
      }
      return value;
    },
    (error: unknown) => {
      if (inflight.get(key) === request) {
        inflight.delete(key);
      }
      throw error;
    },
  );

  inflight.set(key, request);
  return request;
}

export async function mapWithConcurrency<T, R>(
  items: readonly T[],
  limit: number,
  mapper: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  if (items.length === 0) {
    return [];
  }

  const results = new Array<R>(items.length);
  let cursor = 0;
  const workers = Math.max(1, Math.min(limit, items.length));

  async function worker() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await mapper(items[index], index);
    }
  }

  await Promise.all(Array.from({ length: workers }, () => worker()));
  return results;
}
