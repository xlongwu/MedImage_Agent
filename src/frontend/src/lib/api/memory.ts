import { getJson, postJson, type ApiRequestOptions } from "./client";
import type { MemoryCandidate, MemoryConsentStatus, MemoryItem, MemoryPage } from "../types/memory";

export type {
  MemoryCandidate,
  MemoryConsentStatus,
  MemoryItem,
  MemoryPage,
  MemoryRevision,
  MemorySource,
} from "../types/memory";

export function getMemoryConsent(projectId: string, options?: ApiRequestOptions) {
  return getJson<MemoryConsentStatus>(`/api/projects/${projectId}/memory/consent`, options);
}

export function setMemoryConsent(
  projectId: string,
  request: {
    command_id: string;
    generate_enabled: boolean;
    use_enabled: boolean;
  },
  options?: ApiRequestOptions,
) {
  return postJson<MemoryConsentStatus>(
    `/api/projects/${projectId}/memory/consent`,
    request,
    options,
  );
}

export function listMemoryItems(projectId: string, options?: ApiRequestOptions, status = "active") {
  return getJson<MemoryPage<MemoryItem>>(
    `/api/projects/${projectId}/memory/items?status=${encodeURIComponent(status)}`,
    options,
  );
}

export function listMemoryCandidates(projectId: string, options?: ApiRequestOptions) {
  return getJson<MemoryPage<MemoryCandidate>>(
    `/api/projects/${projectId}/memory/candidates?status=proposed`,
    options,
  );
}

export function reviewMemoryCandidate(
  projectId: string,
  candidate: MemoryCandidate,
  accept: boolean,
  commandId: string,
  edits?: { edited_value?: Record<string, unknown>; edited_summary?: string },
  options?: ApiRequestOptions,
) {
  return postJson<Record<string, unknown>>(
    `/api/projects/${projectId}/memory/candidates/${candidate.candidate_id}/${accept ? "accept" : "reject"}`,
    {
      command_id: commandId,
      expected_candidate_version: candidate.candidate_version,
      candidate_hash: candidate.candidate_hash,
      ...edits,
    },
    options,
  );
}

export function pinMemoryItem(
  projectId: string,
  item: MemoryItem,
  pinned: boolean,
  commandId: string,
  options?: ApiRequestOptions,
) {
  return postJson<Record<string, unknown>>(
    `/api/projects/${projectId}/memory/items/${item.memory_id}/pin`,
    {
      command_id: commandId,
      expected_item_version: item.item_version,
      pinned,
    },
    options,
  );
}

export function forgetMemoryItem(
  projectId: string,
  item: MemoryItem,
  commandId: string,
  options?: ApiRequestOptions,
) {
  return postJson<Record<string, unknown>>(
    `/api/projects/${projectId}/memory/items/${item.memory_id}/forget`,
    {
      command_id: commandId,
      expected_item_version: item.item_version,
      expected_revision_hash: item.revision.content_hash,
    },
    options,
  );
}

export function restoreMemoryItem(
  projectId: string,
  item: MemoryItem,
  value: Record<string, unknown>,
  summary: string,
  commandId: string,
  options?: ApiRequestOptions,
) {
  return postJson<Record<string, unknown>>(
    `/api/projects/${projectId}/memory/items/${item.memory_id}/restore`,
    {
      command_id: commandId,
      expected_item_version: item.item_version,
      expected_revision_hash: item.revision.content_hash,
      value,
      summary,
    },
    options,
  );
}

export function memoryCommandId(prefix: string): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `memory-${prefix}-${suffix}`;
}
