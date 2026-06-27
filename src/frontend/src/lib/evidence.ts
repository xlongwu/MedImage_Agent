export type EvidenceLevel =
  | "backend_required"
  | "planned"
  | "metadata_only"
  | "preview_only"
  | "created"
  | "computed"
  | "validated"
  | "validation_failed"
  | "blocked"
  | "unavailable";

export type EvidenceTone = "neutral" | "info" | "success" | "warning" | "danger";

export type EvidenceDefinition = {
  description: string;
  label: string;
  tone: EvidenceTone;
};

const EVIDENCE_DEFINITIONS: Record<EvidenceLevel, EvidenceDefinition> = {
  backend_required: {
    description: "Backend evidence is required before this state can be treated as complete.",
    label: "Backend evidence required",
    tone: "warning",
  },
  planned: {
    description: "The item is expected by a plan or workflow, but no persisted output exists.",
    label: "Planned only",
    tone: "neutral",
  },
  metadata_only: {
    description: "Metadata exists without enough persisted numerical or artifact evidence.",
    label: "Metadata only",
    tone: "warning",
  },
  preview_only: {
    description: "Preview evidence exists without export, validation, or full artifact handoff.",
    label: "Preview-only",
    tone: "info",
  },
  created: {
    description: "A backend-indexed persisted artifact or record exists.",
    label: "Created",
    tone: "success",
  },
  computed: {
    description: "A declared numerical artifact was produced and can be reloaded.",
    label: "Computed",
    tone: "success",
  },
  validated: {
    description: "Validation evidence exists for the persisted result.",
    label: "Validated",
    tone: "success",
  },
  validation_failed: {
    description: "Backend validation evidence reports a failed or incomplete result.",
    label: "Validation failed",
    tone: "danger",
  },
  blocked: {
    description: "Required inputs or safety gates are missing.",
    label: "Blocked",
    tone: "warning",
  },
  unavailable: {
    description: "No executable or previewable implementation is available in this context.",
    label: "Unavailable",
    tone: "neutral",
  },
};

export function evidenceDefinition(level: EvidenceLevel): EvidenceDefinition {
  return EVIDENCE_DEFINITIONS[level];
}

export function evidenceLabel(level: EvidenceLevel): string {
  return evidenceDefinition(level).label;
}

export function evidenceTone(level: EvidenceLevel): EvidenceTone {
  return evidenceDefinition(level).tone;
}
