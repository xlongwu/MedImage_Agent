import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  deleteJson,
  getHealth,
  getJson,
  postJson,
  requestJson,
  toWebSocketUrl,
} from "../client";

function response(body: string, ok = true, status = ok ? 200 : 500): Response {
  return {
    ok,
    status,
    text: () => Promise.resolve(body),
  } as Response;
}

function mockFetch() {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getJson", () => {
  it("sends GET and parses JSON", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"ok":true}'));

    await expect(getJson<{ ok: boolean }>("/api/demo", { baseUrl: "http://api" })).resolves.toEqual(
      { ok: true },
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/api/demo",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("throws with detail message on 500", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"detail":"server failed"}', false));

    await expect(getJson("/api/demo", { baseUrl: "http://api" })).rejects.toThrow("server failed");
  });

  it("retries one transient network failure for an idempotent GET", async () => {
    const fetchMock = mockFetch();
    fetchMock
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(response('{"ok":true}'));

    await expect(getJson("/api/demo", { baseUrl: "http://api" })).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("preserves the structured application error envelope without exposing raw JSON", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(
      response(
        JSON.stringify({
          ok: false,
          error: {
            code: "AGENT_EXECUTION_BLOCKED",
            message: "AGENT_EXECUTION_BLOCKED: REVIEWED_EXECUTION_DISABLED",
            details: {
              blocked_status: "REVIEWED_EXECUTION_DISABLED",
              required_environment: ["MEDIMAGE_ENABLE_REVIEWED_EXECUTION"],
            },
          },
          request_id: "request-1",
        }),
        false,
        403,
      ),
    );

    const promise = getJson("/api/demo", { baseUrl: "http://api" });

    await expect(promise).rejects.toMatchObject({
      code: "AGENT_EXECUTION_BLOCKED",
      details: {
        blocked_status: "REVIEWED_EXECUTION_DISABLED",
        required_environment: ["MEDIMAGE_ENABLE_REVIEWED_EXECUTION"],
      },
      message: "AGENT_EXECUTION_BLOCKED: REVIEWED_EXECUTION_DISABLED",
      requestId: "request-1",
      status: 403,
    } satisfies Partial<ApiError>);
  });

  it("handles empty response body", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response(""));

    await expect(getJson("/api/empty", { baseUrl: "http://api" })).resolves.toEqual({});
  });

  it("stores invalid JSON response text in detail payload", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response("plain text"));

    await expect(getJson("/api/text", { baseUrl: "http://api" })).resolves.toEqual({
      detail: "plain text",
    });
  });
});

describe("postJson", () => {
  it("sends POST with JSON body", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"id":"1"}'));

    await postJson("/api/items", { name: "demo" }, { baseUrl: "http://api" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/api/items",
      expect.objectContaining({
        method: "POST",
        body: '{"name":"demo"}',
      }),
    );
  });

  it("handles network error", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockRejectedValue(new Error("offline"));

    await expect(postJson("/api/items", {}, { baseUrl: "http://api" })).rejects.toThrow("offline");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("deleteJson", () => {
  it("sends DELETE request", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"deleted":true}'));

    await expect(
      deleteJson<{ deleted: boolean }>("/api/items/1", { baseUrl: "http://api" }),
    ).resolves.toEqual({ deleted: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/api/items/1",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });
});

describe("getHealth", () => {
  it("fetches /api/health endpoint", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"status":"ok"}'));

    await expect(getHealth("http://api")).resolves.toEqual({ status: "ok" });

    expect(fetchMock).toHaveBeenCalledWith("http://api/api/health", expect.objectContaining({}));
  });

  it("throws on non-200 status", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"detail":"not healthy"}', false));

    await expect(getHealth("http://api")).rejects.toThrow("not healthy");
  });
});

describe("requestJson utilities", () => {
  it("merges custom headers with JSON header", async () => {
    const fetchMock = mockFetch();
    fetchMock.mockResolvedValue(response('{"ok":true}'));

    await requestJson("/api/demo", {
      baseUrl: "http://api",
      headers: { "X-Test": "1" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/api/demo",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-Test": "1",
        }),
      }),
    );
  });

  it("converts HTTP API URLs to websocket URLs", () => {
    expect(toWebSocketUrl("http://127.0.0.1:8000", "/api/ws")).toBe("ws://127.0.0.1:8000/api/ws");
    expect(toWebSocketUrl("https://example.test", "/api/ws")).toBe("wss://example.test/api/ws");
  });
});
