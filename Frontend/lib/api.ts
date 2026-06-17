"use client";

import { refreshFastApiToken } from "@/lib/auth-token";
import { useAuthStore } from "@/stores/auth-store";
import type { ApiErrorPayload } from "@/types/api";

type QueryPrimitive = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryPrimitive | readonly QueryPrimitive[]>;

interface ApiClientOptions extends Omit<RequestInit, "body" | "headers"> {
  body?: unknown;
  headers?: HeadersInit;
  params?: QueryParams;
  skipAuth?: boolean;
}

const API_BASE_URL = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"}/api/v1`;

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

function normalizePath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

function appendQueryParams(url: URL, params?: QueryParams): void {
  if (!params) {
    return;
  }

  Object.entries(params).forEach(([key, value]) => {
    if (isQueryPrimitiveArray(value)) {
      value.forEach((item) => appendQueryValue(url, key, item));
      return;
    }

    appendQueryValue(url, key, value);
  });
}

function isQueryPrimitiveArray(value: QueryPrimitive | readonly QueryPrimitive[]): value is readonly QueryPrimitive[] {
  return Array.isArray(value);
}

function appendQueryValue(url: URL, key: string, value: QueryPrimitive): void {
  if (value === undefined || value === null || value === "") {
    return;
  }

  url.searchParams.append(key, String(value));
}

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(`${normalizeBaseUrl(API_BASE_URL)}${normalizePath(path)}`);
  appendQueryParams(url, params);
  return url.toString();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringifyDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail === undefined || detail === null) {
    return fallback;
  }

  try {
    return JSON.stringify(detail);
  } catch {
    return fallback;
  }
}

async function parseApiError(response: Response): Promise<ApiErrorPayload> {
  const fallbackDetail = response.statusText || "Request failed";
  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    const text = await response.text();
    return {
      code: `HTTP_${response.status}`,
      detail: text || fallbackDetail,
      status: response.status,
    };
  }

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!isRecord(payload)) {
    return {
      code: `HTTP_${response.status}`,
      detail: fallbackDetail,
      status: response.status,
    };
  }

  return {
    code: typeof payload.code === "string" ? payload.code : `HTTP_${response.status}`,
    detail: stringifyDetail(payload.detail, fallbackDetail),
    status: response.status,
  };
}

async function resolveAuthToken(skipAuth?: boolean): Promise<string | null> {
  if (skipAuth) {
    return null;
  }

  const existingToken = useAuthStore.getState().accessToken;
  if (existingToken) {
    return existingToken;
  }

  try {
    return await refreshFastApiToken();
  } catch {
    return null;
  }
}

async function buildHeaders(options: ApiClientOptions): Promise<Headers> {
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  const token = await resolveAuthToken(options.skipAuth);

  if (!isFormData && options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return headers;
}

function requestBody(body: unknown): BodyInit | undefined {
  if (body === undefined) {
    return undefined;
  }

  if (body instanceof FormData) {
    return body;
  }

  return JSON.stringify(body);
}

async function executeRequest<T>(path: string, options: ApiClientOptions): Promise<T> {
  const response = await fetch(buildUrl(path, options.params), {
    ...options,
    body: requestBody(options.body),
    headers: await buildHeaders(options),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as T;
  }

  return (await response.json()) as T;
}

export async function apiClient<T>(path: string, options: ApiClientOptions = {}): Promise<T> {
  return executeRequest<T>(path, options);
}

export const api = {
  delete: <T>(path: string, options: Omit<ApiClientOptions, "body" | "method"> = {}) =>
    apiClient<T>(path, { ...options, method: "DELETE" }),
  get: <T>(path: string, params?: QueryParams, options: Omit<ApiClientOptions, "body" | "method" | "params"> = {}) =>
    apiClient<T>(path, { ...options, method: "GET", params }),
  patch: <T, TBody = unknown>(
    path: string,
    body: TBody,
    options: Omit<ApiClientOptions, "body" | "method"> = {},
  ) => apiClient<T>(path, { ...options, body, method: "PATCH" }),
  post: <T, TBody = unknown>(
    path: string,
    body?: TBody,
    options: Omit<ApiClientOptions, "body" | "method"> = {},
  ) => apiClient<T>(path, { ...options, body, method: "POST" }),
  postForm: <T>(path: string, formData: FormData, options: Omit<ApiClientOptions, "body" | "method"> = {}) =>
    apiClient<T>(path, { ...options, body: formData, method: "POST" }),
};
