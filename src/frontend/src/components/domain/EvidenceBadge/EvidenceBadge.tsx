import { Badge, type BadgeProps } from "../../ui";
import { evidenceDefinition, type EvidenceLevel } from "../../../lib/evidence";

export type EvidenceBadgeProps = Omit<BadgeProps, "tone"> & {
  level: EvidenceLevel;
};

export function EvidenceBadge({ children, level, title, ...props }: EvidenceBadgeProps) {
  const definition = evidenceDefinition(level);

  return (
    <Badge {...props} title={title ?? definition.description} tone={definition.tone}>
      {children ?? definition.label}
    </Badge>
  );
}
