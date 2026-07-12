import { Badge, type BadgeProps } from "../../ui";
import { useI18n } from "../../../i18n/useI18n";
import { evidenceDefinition, type EvidenceLevel } from "../../../lib/evidence";

export type EvidenceBadgeProps = Omit<BadgeProps, "tone"> & {
  level: EvidenceLevel;
};

export function EvidenceBadge({ children, level, title, ...props }: EvidenceBadgeProps) {
  const { t } = useI18n();
  const definition = evidenceDefinition(level);
  const localized = localizedEvidenceDefinition(level, t);

  return (
    <Badge {...props} title={title ?? localized.description} tone={definition.tone}>
      {children ?? localized.label}
    </Badge>
  );
}

function localizedEvidenceDefinition(level: EvidenceLevel, t: ReturnType<typeof useI18n>["t"]) {
  const keys = {
    backend_required: ["evidence.backendRequired.label", "evidence.backendRequired.description"],
    planned: ["evidence.planned.label", "evidence.planned.description"],
    metadata_only: ["evidence.metadataOnly.label", "evidence.metadataOnly.description"],
    preview_only: ["evidence.previewOnly.label", "evidence.previewOnly.description"],
    created: ["evidence.created.label", "evidence.created.description"],
    computed: ["evidence.computed.label", "evidence.computed.description"],
    validated: ["evidence.validated.label", "evidence.validated.description"],
    validation_failed: ["evidence.validationFailed.label", "evidence.validationFailed.description"],
    blocked: ["evidence.blocked.label", "evidence.blocked.description"],
    unavailable: ["evidence.unavailable.label", "evidence.unavailable.description"],
  } as const;
  const [labelKey, descriptionKey] = keys[level];
  return { description: t(descriptionKey), label: t(labelKey) };
}
