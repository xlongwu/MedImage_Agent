let cachedBaseUrl: string | null = null;

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

export function toWebSocketUrl(baseUrl: string, path: string): string {
  const url = new URL(path, baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const baseUrl = await getApiBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  let payload: unknown = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { detail: text };
  }
  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : text;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload as T;
}

export function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path);
}

export function postJson<T>(path: string, payload: unknown): Promise<T> {
  return requestJson<T>(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
