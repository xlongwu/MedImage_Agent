import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  listMemoryItems,
  pinMemoryItem,
  restoreMemoryItem,
  reviewMemoryCandidate,
  type MemoryCandidate,
  type MemoryItem,
} from "../memory";

const fetchMock = vi.fn();

const item: MemoryItem = {
  memory_id: "memory-1",
  project_id: "project-1",
  kind: "user_preference",
  canonical_key: "user_preference:language",
  item_version: 3,
  generation: 1,
  status: "forgotten",
  pinned: false,
  revision: {
    revision_id: "revision-1",
    revision_number: 2,
    generation: 1,
    content: {},
    content_text: "",
    content_hash: "revision-hash",
    impact_class: "presentation",
  },
  sources: [],
};

const candidate = {
  candidate_id: "candidate-1",
  kind: "workflow_lesson",
  canonical_key: "workflow_lesson:retry",
  content_text: "Retry after review.",
  impact_class: "workflow",
  candidate_version: 2,
  candidate_hash: "candidate-hash",
  source: {
    source_type: "observation",
    source_id: "observation-1",
    source_hash: "source-hash",
    source_ref: "observation:observation-1",
    source_trust_class: "authoritative_structured",
  },
} satisfies MemoryCandidate;

describe("memory API", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  it("encodes item status and optimistic review fields", async () => {
    await listMemoryItems("project/one", { baseUrl: "http://localhost" }, "forgotten");
    expect(fetchMock.mock.calls[0][0]).toContain("status=forgotten");

    fetchMock.mockResolvedValueOnce(
      new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    await reviewMemoryCandidate(
      "project-1",
      candidate,
      true,
      "memory-command-0001",
      { edited_summary: "Reviewed retry guidance." },
      { baseUrl: "http://localhost" },
    );
    const request = fetchMock.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(request.body))).toMatchObject({
      expected_candidate_version: 2,
      candidate_hash: "candidate-hash",
      edited_summary: "Reviewed retry guidance.",
    });
  });

  it("sends version-bound pin and restore commands", async () => {
    fetchMock.mockImplementation(
      async () =>
        new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    await pinMemoryItem("project-1", item, true, "memory-pin-0001", {
      baseUrl: "http://localhost",
    });
    await restoreMemoryItem(
      "project-1",
      item,
      { language: "zh-CN" },
      "Restored preference",
      "memory-restore-0001",
      { baseUrl: "http://localhost" },
    );
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toMatchObject({
      expected_item_version: 3,
      pinned: true,
    });
    expect(JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body))).toMatchObject({
      expected_item_version: 3,
      expected_revision_hash: "revision-hash",
      value: { language: "zh-CN" },
    });
  });
});
