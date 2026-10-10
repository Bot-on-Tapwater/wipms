// Small wrapper around fetch for talking to the backend API.
//
// - Adds the access token to every request.
// - When the access token has expired (401), uses the refresh token once to
//   get a new pair and repeats the request. If that fails the user is sent
//   back to the login page.
// - Turns error responses ({"detail": ...}) into an ApiError with a readable
//   message, which pages show in a toast.

import type { TokenPair } from "./types";

// Set at build time (see .env.example). Defaults to the local backend.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${API_URL}/api/v1`;

const ACCESS_KEY = "ijenga_access_token";
const REFRESH_KEY = "ijenga_refresh_token";

/** Error from an API call; status is the HTTP status (0 when the server cannot be reached). */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// ---------- tokens ----------

/** Reads localStorage; returns null when the browser blocks storage. */
function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** The stored access token, if any. */
export function getAccessToken(): string | null {
  return readStorage(ACCESS_KEY);
}

/** The stored refresh token, if any. */
export function getRefreshToken(): string | null {
  return readStorage(REFRESH_KEY);
}

/** Stores a new access and refresh token pair. */
export function saveTokens(tokens: TokenPair): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

/** Removes both tokens. */
export function clearTokens(): void {
  try {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  } catch {
    // Storage blocked: nothing to clear.
  }
}

// A refresh token can only be used once, so if several requests fail at the
// same time they all wait for the same refresh instead of starting their own.
let refreshInProgress: Promise<boolean> | null = null;

/** Swaps the refresh token for a new token pair. Returns false if that fails. */
async function refreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      return false;
    }
    saveTokens(await response.json());
    return true;
  } catch {
    return false;
  }
}

/** Starts a token refresh, or joins the one already running. */
function refreshOnce(): Promise<boolean> {
  if (!refreshInProgress) {
    refreshInProgress = refreshTokens().finally(() => {
      refreshInProgress = null;
    });
  }
  return refreshInProgress;
}

// ---------- errors ----------

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

// FastAPI returns either {"detail": "message"} or, for invalid input,
// {"detail": [{"loc": ["body", "email"], "msg": "..."}]}.
function messageFromDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const issue = detail[0] as ValidationIssue;
    const message = (issue.msg || "Invalid value").replace(/^Value error, /, "");
    const field = issue.loc ? issue.loc[issue.loc.length - 1] : "";
    if (typeof field === "string" && field !== "body") {
      return `${field.replaceAll("_", " ")}: ${message}`;
    }
    return message;
  }
  return "Something went wrong";
}

/** Turns an error response into an ApiError with a readable message. */
async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    message = messageFromDetail(body.detail);
  } catch {
    // Not JSON: keep the generic message.
  }
  return new ApiError(message, response.status);
}

/** Returns a readable message for anything thrown by an API call. */
export function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong";
}

// ---------- requests ----------

export type QueryValue = string | number | boolean | null | undefined;

/** Builds "?a=1&b=2", leaving out empty values. */
export function buildQuery(query?: Record<string, QueryValue>): string {
  if (!query) {
    return "";
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: FormData;
}

/** Sends one request with the access token and a JSON or form body. */
function sendRequest(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }
  return fetch(`${API_BASE}${path}`, { method: options.method || "GET", headers, body });
}

/** Clears the tokens and opens the login page with a "session expired" note. */
function goToLogin(): void {
  clearTokens();
  if (!window.location.pathname.startsWith("/login")) {
    // A full page load (not router.push) so no state of the old session is kept.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login?expired=1";
  }
}

/** Sends a request and returns the raw response, refreshing the token if needed. */
async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  let response: Response;
  try {
    response = await sendRequest(path, options);
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection.", 0);
  }
  const hadToken = getAccessToken() !== null;
  if (response.status === 401 && hadToken) {
    const refreshed = await refreshOnce();
    if (!refreshed) {
      goToLogin();
      throw new ApiError("Your session has expired. Please log in again.", 401);
    }
    response = await sendRequest(path, options);
  }
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response;
}

/** Sends a request and returns the parsed JSON body. */
async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await request(path, options);
  return (await response.json()) as T;
}

/** One function per HTTP method. Each returns the parsed JSON response. */
export const api = {
  /** GET request with optional query parameters. */
  get<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
    return requestJson<T>(path + buildQuery(query));
  },
  /** POST request with a JSON body. */
  post<T>(path: string, json?: unknown): Promise<T> {
    return requestJson<T>(path, { method: "POST", json: json ?? {} });
  },
  /** PUT request with a JSON body. */
  put<T>(path: string, json?: unknown): Promise<T> {
    return requestJson<T>(path, { method: "PUT", json: json ?? {} });
  },
  /** PATCH request with a JSON body. */
  patch<T>(path: string, json: unknown): Promise<T> {
    return requestJson<T>(path, { method: "PATCH", json });
  },
  /** DELETE request. */
  delete<T>(path: string): Promise<T> {
    return requestJson<T>(path, { method: "DELETE" });
  },
  /** Sends a multipart form (used for image uploads). */
  upload<T>(path: string, form: FormData): Promise<T> {
    return requestJson<T>(path, { method: "POST", form });
  },
  /** Downloads a file (images, PDF reports) as a Blob. */
  async blob(path: string, query?: Record<string, QueryValue>): Promise<Blob> {
    const response = await request(path + buildQuery(query));
    return response.blob();
  },
  /** Downloads a text response (printable HTML reports). */
  async text(path: string, query?: Record<string, QueryValue>): Promise<string> {
    const response = await request(path + buildQuery(query));
    return response.text();
  },
};
