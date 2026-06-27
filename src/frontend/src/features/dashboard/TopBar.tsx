import { memo, useCallback, useState } from "react";

import { Button, IconButton, Tooltip } from "../../components/ui";
import styles from "./TopBar.module.css";

export const TopBar = memo(function TopBar({
  health,
  apiError,
  onRetry,
  projectName,
  activePageLabel,
  onOpenAssistant,
  onOpenInspector,
}: {
  health: boolean | null;
  apiError: string;
  onRetry: () => void;
  projectName: string;
  activePageLabel: string;
  onOpenAssistant: () => void;
  onOpenInspector: () => void;
}) {
  const [copyStatus, setCopyStatus] = useState("");
  const healthDotClass =
    health === true
      ? `${styles.healthDot} ${styles.healthOnline}`
      : health === false
        ? `${styles.healthDot} ${styles.healthOffline}`
        : `${styles.healthDot} ${styles.healthChecking}`;
  const healthLabel =
    health === true ? "Backend connected" : health === false ? "Backend offline" : "Connecting...";
  const handleCopyDiagnostics = useCallback(async () => {
    const diagnostics = [
      `Health: ${healthLabel}`,
      `Project: ${projectName || "Select project"}`,
      `Workspace: ${activePageLabel}`,
      `Error: ${apiError || "none"}`,
    ].join("\n");
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard unavailable");
      }
      await navigator.clipboard.writeText(diagnostics);
      setCopyStatus("Diagnostics copied");
    } catch {
      setCopyStatus("Clipboard unavailable");
    }
  }, [activePageLabel, apiError, healthLabel, projectName]);

  return (
    <>
      <header className={styles.topbar}>
        <div className={styles.caption}>
          <span className={styles.spark}>M</span>
          <strong>MedImage Agent</strong>
        </div>
        <div className={styles.context} aria-label="Current workspace context">
          <span>Project</span>
          <strong>{projectName || "Select project"}</strong>
          <i aria-hidden="true" />
          <small>{activePageLabel}</small>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.healthButton}
            onClick={health === false ? onRetry : undefined}
            title={healthLabel}
            aria-label={healthLabel}
          >
            <span className={healthDotClass} aria-hidden="true" />
            <span className={styles.healthLabel}>{healthLabel}</span>
          </button>
          <Button
            aria-label="Open assistant"
            className={styles.assistantButton}
            leadingIcon={<SparkIcon />}
            onClick={onOpenAssistant}
            title="Open assistant (Ctrl+J)"
            variant="secondary"
          >
            Assistant
          </Button>
          <Tooltip label="Open inspector">
            <IconButton label="Open inspector" onClick={onOpenInspector} variant="secondary">
              <InspectorIcon />
            </IconButton>
          </Tooltip>
        </div>
      </header>
      {apiError ? (
        <div className={styles.banner} role="alert">
          <div className={styles.message}>
            <strong>{healthLabel}</strong>
            <span>{apiError}</span>
            {copyStatus ? <small>{copyStatus}</small> : null}
          </div>
          <div className={styles.bannerActions}>
            <Button onClick={onRetry} size="sm" variant="secondary">
              Retry
            </Button>
            <Button onClick={handleCopyDiagnostics} size="sm" variant="secondary">
              Copy diagnostics
            </Button>
          </div>
        </div>
      ) : null}
    </>
  );
});

function SparkIcon() {
  return (
    <svg className={styles.assistantIcon} viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
        d="M8 2.5l1.1 3.2L12.5 7 9.1 8.3 8 11.5 6.9 8.3 3.5 7l3.4-1.3L8 2.5z"
      />
    </svg>
  );
}

function InspectorIcon() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
        d="M3 3.5h10M3 8h10M3 12.5h6"
      />
      <path
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
        d="M11.5 11l1.5 1.5 2-2"
      />
    </svg>
  );
}
