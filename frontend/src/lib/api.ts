const BASE = "/admin/api";

let _token = "";

export function setToken(token: string) {
  _token = token;
}

export function getToken(): string {
  return _token;
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`API error ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${BASE}${endpoint}`;
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) ?? {}),
  };

  // Content-Type только для запросов с телом
  if (options?.body) {
    headers["Content-Type"] = "application/json";
  }

  // Bearer token если задан
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });

  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }

  return res.json() as Promise<T>;
}
