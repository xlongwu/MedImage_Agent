import type { ReactNode } from "react";

import {
  Badge,
  Button,
  Card,
  type BadgeProps,
  type ButtonProps,
  type CardProps,
} from "../../ui";
import { EvidenceBadge } from "../EvidenceBadge";
import type { EvidenceLevel } from "../../../lib/evidence";
import styles from "./TechnicalModuleSection.module.css";

type TechnicalModuleSectionProps = {
  actionDisabled?: boolean;
  actionSize?: ButtonProps["size"];
  actionVariant?: ButtonProps["variant"];
  ariaLabel: string;
  bodyClassName?: string;
  bodyVisible?: boolean;
  children?: ReactNode;
  className?: string;
  description: ReactNode;
  disabledReason?: ReactNode;
  evidenceLevel?: EvidenceLevel;
  fallback?: ReactNode;
  helperText?: ReactNode;
  hideActionLabel?: string;
  isOpen?: boolean;
  onToggle?: () => void;
  openLabel?: string;
  safetyNote?: ReactNode;
  status: ReactNode;
  statusTone?: BadgeProps["tone"];
  title: ReactNode;
  tone?: CardProps["tone"];
};

const DEFAULT_SAFETY_NOTE =
  "Backend gates remain authoritative; opening this section does not execute tools or mark artifacts computed.";

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function TechnicalModuleSection({
  actionDisabled = false,
  actionSize = "md",
  actionVariant,
  ariaLabel,
  bodyClassName,
  bodyVisible,
  children,
  className,
  description,
  disabledReason,
  evidenceLevel,
  fallback,
  helperText,
  hideActionLabel,
  isOpen = false,
  onToggle,
  openLabel,
  safetyNote = DEFAULT_SAFETY_NOTE,
  status,
  statusTone = "info",
  title,
  tone = "muted",
}: TechnicalModuleSectionProps) {
  const hasToggle = Boolean(onToggle && openLabel && hideActionLabel);
  const shouldShowBody = bodyVisible ?? (hasToggle ? isOpen && !actionDisabled : true);
  const resolvedHelperText = actionDisabled && disabledReason ? disabledReason : helperText;
  const resolvedVariant = actionVariant ?? (isOpen ? "secondary" : "primary");

  return (
    <section className={cx(styles.section, className)} aria-label={ariaLabel}>
      <Card className={styles.intro} tone={tone}>
        <div className={styles.header}>
          <div className={styles.copy}>
            <h3>{title}</h3>
            <p>{description}</p>
          </div>
          {evidenceLevel ? (
            <EvidenceBadge level={evidenceLevel}>{status}</EvidenceBadge>
          ) : (
            <Badge tone={statusTone}>{status}</Badge>
          )}
        </div>
        {hasToggle || resolvedHelperText ? (
          <div className={styles.actions}>
            {hasToggle ? (
              <Button
                disabled={actionDisabled}
                onClick={onToggle}
                size={actionSize}
                variant={resolvedVariant}
              >
                {isOpen ? hideActionLabel : openLabel}
              </Button>
            ) : null}
            {resolvedHelperText ? <span>{resolvedHelperText}</span> : null}
          </div>
        ) : null}
        {safetyNote ? <p className={styles.safetyNote}>{safetyNote}</p> : null}
      </Card>

      {shouldShowBody && children ? (
        <div className={cx(styles.body, bodyClassName)}>{children}</div>
      ) : fallback ? (
        <div className={styles.fallback}>{fallback}</div>
      ) : null}
    </section>
  );
}
