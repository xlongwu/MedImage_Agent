import { useMemo, useState } from "react";
import { Badge, Button, Dialog, EmptyState, Table, TableEmpty } from "../../components/ui";
import type { ProjectSummary } from "../../lib/types/project";
import styles from "./ProjectsPage.module.css";

type ProjectFilter = "all" | "needs_setup" | "active_pipeline" | "rsfmri" | "mri";

export interface ProjectsPageProps {
  deletingProjectId: string | null;
  error: string;
  loading: boolean;
  onClose: () => void;
  onCreateProject: () => void;
  onDeleteProject: (id: string, name: string) => void;
  onSelectProject: (id: string) => void;
  projects: ProjectSummary[];
  selectedProjectId: string | null;
}

const filters: Array<{ id: ProjectFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "needs_setup", label: "Needs setup" },
  { id: "active_pipeline", label: "Pipeline set" },
  { id: "rsfmri", label: "rs-fMRI" },
  { id: "mri", label: "MRI" },
];

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
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<ProjectFilter>("all");
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);

  const filteredProjects = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return projects.filter((project) => {
      const stage = inferProjectStage(project);
      const haystack = [
        project.name,
        project.study_id,
        project.modality,
        project.current_pipeline_id,
        stage.label,
      ]
        .join(" ")
        .toLowerCase();
      const matchesQuery = !needle || haystack.includes(needle);
      const matchesFilter =
        activeFilter === "all" ||
        (activeFilter === "needs_setup" && stage.id === "needs_setup") ||
        (activeFilter === "active_pipeline" && stage.id !== "needs_setup") ||
        (activeFilter === "rsfmri" && project.modality.toLowerCase().includes("rs-fmri")) ||
        (activeFilter === "mri" && project.modality.toLowerCase().includes("mri"));

      return matchesQuery && matchesFilter;
    });
  }, [activeFilter, projects, query]);

  const totalSubjects = projects.reduce((sum, project) => sum + project.subjects_count, 0);
  const activePipelineCount = projects.filter(
    (project) => inferProjectStage(project).id !== "needs_setup",
  ).length;
  const rsfmriCount = projects.filter((project) =>
    project.modality.toLowerCase().includes("rs-fmri"),
  ).length;

  const handleSelectProject = (id: string) => {
    onSelectProject(id);
    onClose();
  };

  const handleDeleteConfirm = () => {
    if (!confirmDelete) return;
    onDeleteProject(confirmDelete.id, confirmDelete.name);
    setConfirmDelete(null);
  };

  return (
    <section className={styles.page} aria-labelledby="projects-page-title">
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Project Library</p>
          <h1 className={styles.title} id="projects-page-title">
            Projects
          </h1>
          <p className={styles.subtitle}>
            Browse local research projects, review pipeline readiness, and open the current
            project context without touching source imaging data.
          </p>
        </div>
        <Button onClick={onCreateProject} variant="primary">
          Add project
        </Button>
      </header>

      <div className={styles.summaryStrip} aria-label="Project summary">
        <div className={styles.summaryItem}>
          <span>Projects</span>
          <strong>{projects.length}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Subjects</span>
          <strong>{totalSubjects}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Pipeline set</span>
          <strong>{activePipelineCount}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>rs-fMRI</span>
          <strong>{rsfmriCount}</strong>
        </div>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.search}>
          <label htmlFor="project-search">Search projects</label>
          <input
            id="project-search"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name, study ID, modality, pipeline"
            type="search"
            value={query}
          />
        </div>
        <div className={styles.filters} aria-label="Project filters">
          {filters.map((filter) => (
            <button
              key={filter.id}
              aria-pressed={activeFilter === filter.id}
              className={styles.filterButton}
              onClick={() => setActiveFilter(filter.id)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {error && projects.length > 0 ? (
        <div className={styles.inlineWarning} role="status">
          Project list loaded with a backend warning. Existing rows are shown from the verified
          response, but no fallback demo projects were added. Error: {error}
        </div>
      ) : null}

      <div className={styles.panel}>
        {loading ? (
          <div className={styles.loadingBody} role="status" aria-label="Loading projects">
            <span className={styles.loadingRow} />
            <span className={styles.loadingRow} />
            <span className={styles.loadingRow} />
          </div>
        ) : error && projects.length === 0 ? (
          <EmptyState
            action={
              <Button onClick={onCreateProject} variant="primary">
                Add project
              </Button>
            }
            description={
              <>
                The backend did not return a verified project list. Showing no project rows avoids
                presenting demo research data as real work. Error: {error}
              </>
            }
            icon={<VoxelGrid />}
            title="Project list unavailable"
          />
        ) : projects.length === 0 ? (
          <EmptyState
            action={
              <Button onClick={onCreateProject} variant="primary">
                Create your first research project
              </Button>
            }
            description="Start by referencing an existing local DICOM or BIDS directory. MedImage Agent keeps source research files read-only."
            icon={<VoxelGrid />}
            title="Create your first research project"
          />
        ) : (
          <Table className={styles.table} caption={error ? `Project list warning: ${error}` : null}>
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Data type</th>
                <th scope="col">Subjects</th>
                <th scope="col">Current stage</th>
                <th scope="col">Last activity</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProjects.length === 0 ? (
                <TableEmpty colSpan={6}>No projects match the current filters.</TableEmpty>
              ) : (
                filteredProjects.map((project) => {
                  const stage = inferProjectStage(project);
                  return (
                    <tr key={project.id}>
                      <td>
                        <div className={styles.projectName}>
                          <strong>{project.name}</strong>
                          <span>{project.study_id}</span>
                          <span className={styles.pipelineCell}>{project.current_pipeline_id}</span>
                        </div>
                      </td>
                      <td>{project.modality}</td>
                      <td>{project.subjects_count}</td>
                      <td>
                        <span className={styles.stageCell}>
                          <Badge tone={stage.tone}>{stage.label}</Badge>
                          <span className={styles.stageSummary}>{stage.summary}</span>
                        </span>
                      </td>
                      <td>
                        <span className={styles.muted}>{project.created_date}</span>
                      </td>
                      <td>
                        <div className={styles.actions}>
                          <Button
                            onClick={() => handleSelectProject(project.id)}
                            variant={project.id === selectedProjectId ? "primary" : "secondary"}
                            size="sm"
                          >
                            {project.id === selectedProjectId ? "Open" : "Select"}
                          </Button>
                          <Button
                            disabled={deletingProjectId === project.id}
                            onClick={() => setConfirmDelete({ id: project.id, name: project.name })}
                            variant="ghost"
                            size="sm"
                          >
                            Remove
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </Table>
        )}
      </div>

      <p className={styles.footerNote}>
        Project rows reference local project metadata only. DICOM, BIDS, NIfTI, rawdata, and source
        research files are never edited from this list view.
      </p>

      <Dialog
        description={
          confirmDelete ? (
            <span>
              Remove <strong>{confirmDelete.name}</strong> from the project list? This preserves
              data on disk and only removes the recent project listing.
            </span>
          ) : null
        }
        footer={
          confirmDelete ? (
            <>
              <Button onClick={() => setConfirmDelete(null)} variant="secondary">
                Cancel
              </Button>
              <Button
                disabled={deletingProjectId === confirmDelete.id}
                onClick={handleDeleteConfirm}
                variant="danger"
              >
                {deletingProjectId === confirmDelete.id ? "Removing..." : "Remove"}
              </Button>
            </>
          ) : null
        }
        onOpenChange={(open) => {
          if (!open) setConfirmDelete(null);
        }}
        open={Boolean(confirmDelete)}
        title="Remove project"
      />
    </section>
  );
}

function VoxelGrid() {
  return (
    <div className={styles.emptyVisual} aria-hidden="true">
      {Array.from({ length: 24 }).map((_, index) => (
        <span className={styles.voxel} key={index} />
      ))}
    </div>
  );
}

type StageId = "needs_setup" | "data" | "plan" | "preprocessing" | "qc" | "results";

function inferProjectStage(project: ProjectSummary): {
  id: StageId;
  label: string;
  summary: string;
  tone: "neutral" | "info" | "success" | "warning" | "danger";
} {
  const pipeline = project.current_pipeline_id.toLowerCase();

  if (!pipeline || pipeline === "not-selected" || pipeline === "none") {
    return {
      id: "needs_setup",
      label: "Needs setup",
      summary: "No reviewed pipeline is selected",
      tone: "warning",
    };
  }

  if (/(qc|quality|validation|report)/.test(pipeline)) {
    return {
      id: "qc",
      label: "QC",
      summary: "Review quality reports and validation evidence",
      tone: "success",
    };
  }

  if (/(result|artifact|alff|falff|reho|connectivity|fc)/.test(pipeline)) {
    return {
      id: "results",
      label: "Results",
      summary: "Artifact or result workspace is linked",
      tone: "info",
    };
  }

  if (/(preprocess|spm|dpabi|realign|normalize|smooth|segmentation)/.test(pipeline)) {
    return {
      id: "preprocessing",
      label: "Preprocessing",
      summary: "Preprocessing configuration or run state exists",
      tone: "info",
    };
  }

  if (/(dicom|bids|conversion|convert)/.test(pipeline)) {
    return {
      id: "data",
      label: "Data",
      summary: "Data preparation or conversion review is linked",
      tone: "info",
    };
  }

  return {
    id: "plan",
    label: "Needs review",
    summary: "Pipeline value is present but not classified as a completed stage",
    tone: "neutral",
  };
}
