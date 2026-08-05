let cachedBaseUrl: string | null = null;

export type ApiRequestOptions = RequestInit & {
  baseUrl?: string;
};

type ApiErrorEnvelope = {
  code?: unknown;
  message?: unknown;
  details?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export class ApiError extends Error {
  readonly code: string | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;
  readonly status: number;

  constructor({
    code,
    details,
    message,
    requestId,
    status,
  }: {
    code?: string | null;
    details?: Record<string, unknown>;
    message: string;
    requestId?: string | null;
    status: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code ?? null;
    this.details = details ?? {};
    this.requestId = requestId ?? null;
    this.status = status;
  }
}

export async function getApiBaseUrl(): Promise<string> {
  if (cachedBaseUrl) {
    return cachedBaseUrl;
  }
  if (window.medimage?.getApiBaseUrl) {
    cachedBaseUrl = await window.medimage.getApiBaseUrl();
    return cachedBaseUrl;
  }
  cachedBaseUrl =
    window.__MEDIMAGE_DESKTOP_CONFIG__?.backendBaseUrl ||
    window.MEDIMAGE_API_BASE_URL ||
    window.MEDIMAGE_DESKTOP_RUNTIME?.apiBaseUrl ||
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000";
  return cachedBaseUrl;
}

export function getFallbackApiBaseUrl(): string {
  return (
    cachedBaseUrl ||
    window.__MEDIMAGE_DESKTOP_CONFIG__?.backendBaseUrl ||
    window.MEDIMAGE_API_BASE_URL ||
    window.MEDIMAGE_DESKTOP_RUNTIME?.apiBaseUrl ||
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000"
  );
}

export const DEFAULT_API_BASE = getFallbackApiBaseUrl();

export function toWebSocketUrl(baseUrl: string, path: string): string {
  const url = new URL(path, baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export async function requestJson<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  const { baseUrl: explicitBaseUrl, headers, ...requestOptions } = options ?? {};
  const baseUrl = explicitBaseUrl ?? (await getApiBaseUrl());
  const requestInit: RequestInit = {
    headers: {
      "Content-Type": "application/json",
      ...(headers || {}),
    },
    ...requestOptions,
  };
  const method = (requestInit.method ?? "GET").toUpperCase();
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, requestInit);
  } catch (error) {
    if (method !== "GET" || requestInit.signal?.aborted) {
      throw error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
    response = await fetch(`${baseUrl}${path}`, requestInit);
  }
  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { detail: text };
  }
  if (!response.ok) {
    const record = isRecord(payload) ? payload : {};
    const envelope = isRecord(record.error) ? (record.error as ApiErrorEnvelope) : null;
    const legacyDetail = "detail" in record ? record.detail : undefined;
    const message =
      typeof envelope?.message === "string"
        ? envelope.message
        : typeof legacyDetail === "string"
          ? legacyDetail
          : legacyDetail !== undefined
            ? JSON.stringify(legacyDetail)
            : text || `HTTP ${response.status}`;

    throw new ApiError({
      code: typeof envelope?.code === "string" ? envelope.code : null,
      details: isRecord(envelope?.details) ? envelope.details : {},
      message,
      requestId: typeof record.request_id === "string" ? record.request_id : null,
      status: response.status,
    });
  }
  return payload as T;
}

export function getJson<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  return requestJson<T>(path, options);
}

export function getHealth(baseUrl = getFallbackApiBaseUrl()): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/health", { baseUrl });
}

export function postJson<T>(
  path: string,
  payload: unknown,
  options?: ApiRequestOptions,
): Promise<T> {
  return requestJson<T>(path, {
    ...options,
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteJson<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  return requestJson<T>(path, {
    ...options,
    method: "DELETE",
  });
}
