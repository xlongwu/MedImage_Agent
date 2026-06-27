import { memo } from "react";

import { Skeleton } from "../../components/ui";
import styles from "./WorkspaceSuspenseFallback.module.css";

export const WorkspaceSuspenseFallback = memo(function WorkspaceSuspenseFallback({
  label,
}: {
  label: string;
}) {
  return (
    <div className={styles.fallback} role="status" aria-label={label} aria-live="polite">
      <div className={styles.copy}>
        <span className={styles.loadingDot} aria-hidden="true" />
        <span>{label}</span>
      </div>
      <div className={styles.skeletonHeader} aria-hidden="true">
        <Skeleton height={18} width="32%" />
        <Skeleton height={12} width="56%" />
      </div>
      <div className={styles.skeletonMetrics} aria-hidden="true">
        <Skeleton height={46} />
        <Skeleton height={46} />
        <Skeleton height={46} />
      </div>
      <div className={styles.skeletonGrid} aria-hidden="true">
        <div className={styles.skeletonPanel}>
          <Skeleton height={14} width="44%" />
          <Skeleton height={12} width="78%" />
          <Skeleton height={12} width="64%" />
          <Skeleton height={88} />
        </div>
        <div className={styles.skeletonPanel}>
          <Skeleton height={14} width="52%" />
          <Skeleton height={12} width="72%" />
          <Skeleton height={12} width="58%" />
          <Skeleton height={88} />
        </div>
      </div>
    </div>
  );
});
