import { useRef, type KeyboardEvent } from "react";

import { Icon } from "../../components/ui";
import { useI18n } from "../../i18n/useI18n";
import type { MessageKey } from "../../i18n/messages/en";
import type { LifecycleItem, PrimaryWorkspace } from "./workspaceModel";
import styles from "./LifecycleRail.module.css";

const labelKeys: Record<PrimaryWorkspace, MessageKey> = {
  overview: "nav.overview",
  data: "nav.data",
  plan: "nav.plan",
  preprocessing: "nav.preprocessing",
  qc: "nav.qc",
  results: "nav.results",
};

export function LifecycleRail({
  activeWorkspace,
  items,
  onNavigate,
}: {
  activeWorkspace: PrimaryWorkspace | null;
  items: LifecycleItem[];
  onNavigate: (workspace: PrimaryWorkspace) => void;
}) {
  const { t } = useI18n();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === "ArrowLeft" ? -1 : 1;
    const target =
      event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : index + direction;
    const nextIndex = Math.min(items.length - 1, Math.max(0, target));
    refs.current[nextIndex]?.focus();
  };

  return (
    <nav aria-label={t("nav.lifecycle")} className={styles.rail}>
      <ol className={styles.list}>
        {items.map((item, index) => {
          const blocked = item.state === "blocked";
          const selected = item.id === activeWorkspace;
          return (
            <li className={styles.item} key={item.id}>
              {index > 0 ? <span aria-hidden="true" className={styles.connector} /> : null}
              <button
                aria-current={selected ? "step" : undefined}
                aria-disabled={blocked}
                className={styles.button}
                data-state={item.state}
                onClick={() => {
                  if (!blocked) onNavigate(item.id);
                }}
                onKeyDown={(event) => handleKeyDown(event, index)}
                ref={(node) => {
                  refs.current[index] = node;
                }}
                title={blocked ? (item.blockedReason ?? t("common.blocked")) : undefined}
                type="button"
              >
                <span className={styles.dot} aria-hidden="true">
                  {item.state === "completed" ? (
                    <Icon height={12} name="circle-check" width={12} />
                  ) : null}
                </span>
                <span>{t(labelKeys[item.id])}</span>
                {blocked && item.blockedReason ? (
                  <span className={styles.srOnly}>{item.blockedReason}</span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
