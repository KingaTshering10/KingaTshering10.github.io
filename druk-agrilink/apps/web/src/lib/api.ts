"use client";

/**
 * Typed API client with automatic access-token refresh.
 *
 * Access token lives in memory; the refresh token is kept in localStorage for
 * PWA session persistence (documented trade-off for the pilot — see
 * docs/SECURITY.md; rotation + family revocation bound the exposure). Tokens
 * are never written into the offline draft store or service-worker caches.
 */

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  request_id?: string;
  [key: string]: unknown;
}

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public error: ApiError,
  ) {
    super(error.message);
  }
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

let accessToken: string | null = null;

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  window.localStorage.setItem("druk.refresh", refresh);
}

export function clearTokens(): void {
  accessToken = null;
  window.localStorage.removeItem("druk.refresh");
}

export function hasSession(): boolean {
  return accessToken !== null || window.localStorage.getItem("druk.refresh") !== null;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = window.localStorage.getItem("druk.refresh");
  if (!refresh) return false;
  const resp = await fetch(`${BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) {
    clearTokens();
    return false;
  }
  const body = (await resp.json()) as { access_token: string; refresh_token: string };
  setTokens(body.access_token, body.refresh_token);
  return true;
}

export async function api<T = unknown>(
  path: string,
  options: { method?: string; body?: unknown; retry?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, retry = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const resp = await fetch(`${BASE}/api/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 401 && retry && (await tryRefresh())) {
    return api<T>(path, { method, body, retry: false });
  }
  if (resp.status === 204) return undefined as T;
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const error: ApiError = (json as { error?: ApiError }).error ?? {
      code: "UNKNOWN",
      message: "Request failed",
    };
    throw new ApiRequestError(resp.status, error);
  }
  return json as T;
}

export async function login(email: string, password: string): Promise<void> {
  const tokens = await api<{ access_token: string; refresh_token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  setTokens(tokens.access_token, tokens.refresh_token);
}

export async function logout(): Promise<void> {
  const refresh = window.localStorage.getItem("druk.refresh");
  if (refresh) {
    await api("/auth/logout", { method: "POST", body: { refresh_token: refresh } }).catch(
      () => undefined,
    );
  }
  clearTokens();
}

export interface Me {
  id: string;
  email: string;
  role: "farmer" | "coordinator" | "buyer" | "transporter" | "admin";
  preferred_language: "en" | "dz";
  is_verified: boolean;
}
