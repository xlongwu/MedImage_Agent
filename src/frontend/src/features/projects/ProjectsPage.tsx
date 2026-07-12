import { useMemo, useState } from "react";

import { Badge, Button, Dialog, EmptyState, Icon } from "../../components/ui";
import { useI18n } from "../../i18n/useI18n";
import type { ProjectSummary } from "../../lib/types/project";
import styles from "./ProjectsPage.module.css";

type ProjectFilter = "all" | "needs_setup" | "pipeline" | "rsfmri" | "mri";

export interface ProjectsPageProps {
  deletingProjectId: string | null;
  error: string;
  loading: boolean;
  onClose?: () => void;
  onCreateProject: () => void;
  onDeleteProject: (id: string, name: string) => void;
  onSelectProject: (id: string) => void;
  projects: ProjectSummary[];
  selectedProjectId: string | null;
}

export function ProjectsPage({
  deletingProjectId,
  error,
  loading,
  onClose,
  onCreateProject,
  onDeleteProject,
  onSelectProject,
  projects,
  selectedProjectId,
}: ProjectsPageProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<ProjectFilter>("all");
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);
  const filters: Array<{ id: ProjectFilter; label: string }> = [
    { id: "all", label: t("projects.all") },
    { id: "needs_setup", label: t("projects.needsSetup") },
    { id: "pipeline", label: t("projects.pipelineSet") },
    { id: "rsfmri", label: "rs-fMRI" },
    { id: "mri", label: "MRI" },
  ];

  const filteredProjects = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return projects.filter((project) => {
      const hasPipeline = hasReviewedPipelineReference(project);
      const haystack = [
        project.name,
        project.study_id,
        project.modality,
        project.current_pipeline_id,
      ]
        .join(" ")
        .toLowerCase();
      return (
        (!needle || haystack.includes(needle)) &&
        (activeFilter === "all" ||
          (activeFilter === "needs_setup" && !hasPipeline) ||
          (activeFilter === "pipeline" && hasPipeline) ||
          (activeFilter === "rsfmri" && project.modality.toLowerCase().includes("rs-fmri")) ||
          (activeFilter === "mri" && project.modality.toLowerCase().includes("mri")))
      );
    });
  }, [activeFilter, projects, query]);

  const selectProject = (projectId: string) => {
    onSelectProject(projectId);
    onClose?.();
  };

  return (
    <section className={styles.page} aria-labelledby="projects-page-title">
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{t("projects.library")}</p>
          <h1 className={styles.title} id="projects-page-title">
            {t("projects.title")}
          </h1>
          <p className={styles.subtitle}>{t("projects.subtitle")}</p>
        </div>
        <Button
          leadingIcon={<Icon height={16} name="plus" width={16} />}
          onClick={onCreateProject}
          variant="primary"
        >
          {t("projects.add")}
        </Button>
      </header>

      <div className={styles.toolbar}>
        <label className={styles.search}>
          <span>{t("projects.search")}</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("projects.searchPlaceholder")}
            type="search"
            value={query}
          />
        </label>
        <div className={styles.filters} aria-label={t("projects.filters")}>
          {filters.map((filter) => (
            <button
              aria-pressed={activeFilter === filter.id}
              className={styles.filterButton}
              key={filter.id}
              onClick={() => setActiveFilter(filter.id)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {error && projects.length > 0 ? (
        <div className={styles.warning} role="status">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div aria-label={t("projects.loading")} className={styles.grid} role="status">
          {Array.from({ length: 6 }).map((_, index) => (
            <span className={styles.skeletonCard} key={index} />
          ))}
        </div>
      ) : error && projects.length === 0 ? (
        <EmptyState
          action={
            <Button onClick={onCreateProject} variant="primary">
              {t("projects.add")}
            </Button>
          }
          description={`${t("projects.errorDescription")} ${error}`}
          icon={<Icon height={22} name="circle-alert" width={22} />}
          title={t("projects.errorTitle")}
        />
      ) : projects.length === 0 ? (
        <EmptyState
          action={
            <Button onClick={onCreateProject} variant="primary">
              {t("projects.emptyAction")}
            </Button>
          }
          description={t("projects.emptyDescription")}
          icon={<Icon height={22} name="folder" width={22} />}
          title={t("projects.emptyTitle")}
        />
      ) : filteredProjects.length === 0 ? (
        <EmptyState title={t("projects.noMatches")} />
      ) : (
        <div className={styles.grid}>
          {filteredProjects.map((project) => {
            const hasPipeline = hasReviewedPipelineReference(project);
            return (
              <article className={styles.card} key={project.id}>
                <button
                  className={styles.cardMain}
                  onClick={() => selectProject(project.id)}
                  type="button"
                >
                  <div className={styles.cardMeta}>
                    <Badge tone="neutral">{project.modality || t("common.unavailable")}</Badge>
                    <span className={styles.state} data-state={hasPipeline ? "ready" : "setup"}>
                      <i aria-hidden="true" />
                      {hasPipeline ? t("projects.pipelineSet") : t("projects.needsSetup")}
                    </span>
                  </div>
                  <h2>{project.name}</h2>
                  <p className={styles.studyId}>{project.study_id}</p>
                  <dl className={styles.cardFacts}>
                    <div>
                      <dt>{t("projects.subjects")}</dt>
                      <dd>{project.subjects_count}</dd>
                    </div>
                    <div>
                      <dt>{t("projects.lastActivity")}</dt>
                      <dd>{project.created_date || t("common.unavailable")}</dd>
                    </div>
                  </dl>
                </button>
                <div className={styles.cardActions}>
                  <Button
                    onClick={() => selectProject(project.id)}
                    size="sm"
                    variant={project.id === selectedProjectId ? "primary" : "secondary"}
                  >
                    {project.id === selectedProjectId ? t("common.open") : t("common.select")}
                  </Button>
                  <Button
                    disabled={deletingProjectId === project.id}
                    onClick={() => setConfirmDelete({ id: project.id, name: project.name })}
                    size="sm"
                    variant="ghost"
                  >
                    {t("common.remove")}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Dialog
        description={
          confirmDelete ? t("projects.removeDescription", { name: confirmDelete.name }) : null
        }
        footer={
          confirmDelete ? (
            <>
              <Button onClick={() => setConfirmDelete(null)} variant="secondary">
                {t("common.cancel")}
              </Button>
              <Button
                disabled={deletingProjectId === confirmDelete.id}
                onClick={() => {
                  onDeleteProject(confirmDelete.id, confirmDelete.name);
                  setConfirmDelete(null);
                }}
                variant="danger"
              >
                {t("common.remove")}
              </Button>
            </>
          ) : null
        }
        onOpenChange={(open) => {
          if (!open) setConfirmDelete(null);
        }}
        open={Boolean(confirmDelete)}
        title={t("projects.removeTitle")}
      />
    </section>
  );
}

function hasReviewedPipelineReference(project: ProjectSummary): boolean {
  const value = project.current_pipeline_id?.trim().toLowerCase();
  return Boolean(value && value !== "none" && value !== "not-selected");
}
