export interface MemoryConsentStatus {
  schema_version: 1;
  project_id: string;
  available: boolean;
  generation_available: boolean;
  use_available: boolean;
  generate_enabled: boolean;
  use_enabled: boolean;
  consent_epoch: number;
  outbox_cutoff_sequence: number;
  updated_at: string | null;
  degraded_reason: string | null;
}

export interface MemorySource {
  source_type: string;
  source_id: string;
  source_hash: string;
  source_ref: string;
  source_trust_class: string;
}

export interface MemoryRevision {
  revision_id: string;
  revision_number: number;
  generation: number;
  content: Record<string, unknown>;
  content_text: string;
  content_hash: string;
  impact_class: string;
}

export interface MemoryItem {
  memory_id: string;
  project_id: string;
  kind: string;
  canonical_key: string;
  item_version: number;
  generation: number;
  status: string;
  pinned: boolean;
  revision: MemoryRevision;
  sources: MemorySource[];
}

export interface MemoryCandidate {
  candidate_id: string;
  kind: string;
  canonical_key: string;
  content_text: string;
  impact_class: string;
  candidate_version: number;
  candidate_hash: string;
  source: MemorySource;
}

export interface MemoryPage<T> {
  items: T[];
  total: number;
  next_cursor: string | null;
}
