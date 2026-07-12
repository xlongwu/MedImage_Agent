import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Button, Dialog } from "../../components/ui";
import type { ProjectSummary } from "../../lib/types/project";
import { useI18n } from "../../i18n/useI18n";
import styles from "./ProjectSwitcher.module.css";

export interface ProjectSwitcherProps {
  projects: ProjectSummary[];
  selectedProjectId: string;
  loading: boolean;
  error: string;
  deletingProjectId: string | null;
  onSelect: (id: string) => void;
  onCreateProject: () => void;
  onOpenProjects: () => void;
  onDelete: (id: string, name: string) => void;
}

export const ProjectSwitcher = memo(function ProjectSwitcher({
  projects,
  selectedProjectId,
  loading,
  error,
  deletingProjectId,
  onSelect,
  onCreateProject,
  onOpenProjects,
  onDelete,
}: ProjectSwitcherProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const selected = projects.find((p) => p.id === selectedProjectId);
  const popoverId = "project-switcher-popover";
  const metaLabel = loading
    ? t("projects.switcher.loading")
    : error
      ? t("projects.switcher.unavailable")
      : t("projects.switcher.count", { count: projects.length });

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setConfirmDelete(null);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        setConfirmDelete(null);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const handleTriggerClick = useCallback(() => {
    setOpen((current) => {
      const next = !current;
      if (!next) {
        setConfirmDelete(null);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (id: string) => {
      onSelect(id);
      setOpen(false);
      triggerRef.current?.focus();
    },
    [onSelect],
  );

  const handleCreateProject = useCallback(() => {
    setOpen(false);
    setConfirmDelete(null);
    onCreateProject();
    triggerRef.current?.focus();
  }, [onCreateProject]);

  const handleOpenProjects = useCallback(() => {
    setOpen(false);
    setConfirmDelete(null);
    onOpenProjects();
    triggerRef.current?.focus();
  }, [onOpenProjects]);

  const handleDeleteRequest = useCallback((id: string, name: string) => {
    setConfirmDelete({ id, name });
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (!confirmDelete) return;
    onDelete(confirmDelete.id, confirmDelete.name);
    setConfirmDelete(null);
  }, [confirmDelete, onDelete]);

  const handleDeleteCancel = useCallback(() => setConfirmDelete(null), []);

  return (
    <div className={styles.switcher} ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? popoverId : undefined}
        onClick={handleTriggerClick}
        title={selected ? selected.name : t("projects.switcher.select")}
      >
        <span className={styles.glyph} aria-hidden="true">
          <svg viewBox="0 0 20 20" width="14" height="14">
            <path
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinejoin="round"
              d="M3 6l7-3 7 3v8l-7 3-7-3V6z M3 6l7 3 7-3 M10 9v8"
            />
          </svg>
        </span>
        <span className={styles.label}>
          <span className={styles.current}>
            {selected ? selected.name : t("projects.switcher.select")}
          </span>
          <small className={styles.meta}>{metaLabel}</small>
        </span>
        <svg className={styles.caret} viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            d={open ? "M4 10l4-4 4 4" : "M4 6l4 4 4-4"}
          />
        </svg>
      </button>

      {open ? (
        <div
          className={styles.popover}
          id={popoverId}
          role="listbox"
          aria-label={t("projects.switcher.aria")}
        >
          <header className={styles.header}>
            <div className={styles.headerCopy}>
              <span>{t("projects.switcher.recent")}</span>
              <small>
                {error
                  ? t("common.unavailable")
                  : t("projects.switcher.available", { count: projects.length })}
              </small>
            </div>
            <div className={styles.headerActions}>
              <button
                type="button"
                className={styles.popoverAction}
                onClick={handleOpenProjects}
                disabled={loading}
              >
                <span>{t("projects.switcher.viewAll")}</span>
              </button>
              <button
                type="button"
                className={styles.popoverAction}
                onClick={handleCreateProject}
                disabled={loading}
              >
                <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
                  <path
                    fill="none"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeWidth="1.7"
                    d="M8 3v10M3 8h10"
                  />
                </svg>
                <span>{t("projects.switcher.add")}</span>
              </button>
            </div>
          </header>
          {projects.length ? (
            <ul className={styles.list}>
              {projects.map((item) => (
                <li
                  key={item.id}
                  className={`${styles.item} ${item.id === selectedProjectId ? styles.selected : ""}`}
                >
                  <button
                    type="button"
                    role="option"
                    aria-selected={item.id === selectedProjectId}
                    className={styles.itemButton}
                    onClick={() => handleSelect(item.id)}
                    title={item.name}
                  >
                    <span className={styles.itemName}>{item.name}</span>
                    {item.id === selectedProjectId ? (
                      <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                        <path
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M3 8.5l3.5 3.5L13 4.5"
                        />
                      </svg>
                    ) : null}
                  </button>
                  <button
                    type="button"
                    className={styles.moreButton}
                    aria-label={t("projects.switcher.moreActions", { name: item.name })}
                    title={t("projects.switcher.moreActionsTitle")}
                    onClick={() => handleDeleteRequest(item.id, item.name)}
                    disabled={deletingProjectId === item.id}
                  >
                    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                      <path
                        fill="currentColor"
                        d="M4 8a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 4 8zm5.2 0a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 9.2 8zm5.2 0a1.2 1.2 0 1 1-2.4 0A1.2 1.2 0 0 1 14.4 8z"
                      />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.empty} role="status">
              {error ? t("projects.switcher.errorEmpty") : t("projects.switcher.empty")}
            </div>
          )}
        </div>
      ) : null}

      <Dialog
        description={
          confirmDelete
            ? t("projects.switcher.removeDescription", { name: confirmDelete.name })
            : null
        }
        footer={
          confirmDelete ? (
            <>
              <Button onClick={handleDeleteCancel} variant="secondary">
                {t("common.cancel")}
              </Button>
              <Button
                disabled={deletingProjectId === confirmDelete.id}
                onClick={handleDeleteConfirm}
                variant="danger"
              >
                {deletingProjectId === confirmDelete.id
                  ? t("projects.switcher.removing")
                  : t("common.remove")}
              </Button>
            </>
          ) : null
        }
        onOpenChange={(nextOpen) => {
          if (!nextOpen) {
            handleDeleteCancel();
          }
        }}
        open={Boolean(confirmDelete)}
        title={t("projects.switcher.removeTitle")}
      />
    </div>
  );
});
