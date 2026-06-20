"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ProjectCreateResponse } from "../../types";
import type { WorkflowTab } from "../../lib/projectWorkflow";
import type { StudyOverview, ProjectSummary } from "../../lib/types/project";
import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type {
  ImagePlane,
  ImagePreview,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ModelStatus } from "../../lib/types/model";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ChatMessage } from "../../lib/types/assistant";
import type { PresetPlanDraft } from "../../types";
import {
  buildProjectInventory,
  isProjectNameConflict,
  mergeCreatedProjectIntoList,
  uniqueProjectName,
} from "../../lib/projectWorkflow";
import { createProjectFromDirectory, deleteProject, getApiBaseUrl } from "../../lib/api";
import { useProject, useProjects } from "../../hooks/useProjects";
import { useProjectOverview } from "../../hooks/useProjectOverview";
import { useDatasetSummary } from "../../hooks/useDatasetSummary";
import { useModelStatus } from "../../hooks/useModelStatus";
import { useImageSources } from "../../hooks/useImageSources";
import { useImagePreview } from "../../hooks/useImagePreview";
import { useImageValidation } from "../../hooks/useImageValidation";
import { useRunPipeline } from "../../hooks/useRunPipeline";
import { useTaskStream } from "../../hooks/useTaskStream";
import { useTasks } from "../../hooks/useTasks";
import { useTaskEvents } from "../../hooks/useTaskEvents";
import { useTaskDiagnostics } from "../../hooks/useTaskDiagnostics";
import type { TaskStreamMessage } from "../../lib/types/task";
import { fallbackChat } from "../../lib/mockData";

export interface ProjectController {
  projects: { data: ProjectSummary[]; loading: boolean; error: string };
  projectsLoading: boolean;
  projectsError: string;
  reloadProjects: () => Promise<ProjectSummary[] | void>;
  project: ReturnType<typeof useProject>["data"];
  projectFromFallback: boolean;
  projectInventory: object;
  overview: StudyOverview;
  overviewLoading: boolean;
  overviewError: string;
  projectDiagnostics: Record<string, unknown>;
  dataset: DatasetSummary;
  model: ModelStatus;
  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;
  selectedProjectForPlanReview: import("../../lib/types/project").ProjectDetail | null;
  selectedProjectMetadata: Record<string, unknown> | undefined;
  sequence: string;
  setSequence: (s: string) => void;
  selectedSubjectId: string | null;
  setSelectedSubjectId: (id: string | null) => void;
  plane: ImagePlane;
  setPlane: (p: ImagePlane) => void;
  sliceIndex: number | null;
  setSliceIndex: (i: number | null) => void;
  sequenceOptions: string[];
  imageSources: ImageSources;
  imageValidation: ImageValidationReport;
  imagePreview: ImagePreview;
  selectedImageSource: ImageSources["manifest"][number] | null;
  imagePreviewLoading: boolean;
  projectCreateLoading: boolean;
  projectCreateError: string;
  projectCreateResult: ProjectCreateResponse | null;
  setProjectCreateResult: (r: ProjectCreateResponse | null) => void;
  setProjectCreateError: (e: string) => void;
  handleUploadData: () => Promise<void>;
  handleDeleteProject: (projectId: string, projectName: string) => Promise<void>;
}

export function useProjectController(
  selectedProjectId: string | null = null,
  setSelectedProjectId: ((id: string | null) => void) | undefined = undefined,
): ProjectController {
  const projects = useProjects();
  const project = useProject(selectedProjectId);
  const overview = useProjectOverview(project.data.study_id);
  const dataset = useDatasetSummary(project.data.id);
  const model = useModelStatus(project.data.id);
  const imageSources = useImageSources(project.data.id);
  const imageValidation = useImageValidation(project.data.id);
  const imagePreview = useImagePreview(project.data.id, "T1", null, null, "axial");

  const [projectCreateLoading, setProjectCreateLoading] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState("");
  const [projectCreateResult, setProjectCreateResult] = useState<ProjectCreateResponse | null>(
    null,
  );
  const [sequence, setSequence] = useState("T1");
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [plane, setPlane] = useState<ImagePlane>("axial");
  const [sliceIndex, setSliceIndex] = useState<number | null>(null);

  const selectedProjectIdRef = selectedProjectId;
  const setSelectedProjectIdRef = setSelectedProjectId;
  const projectsRef = projects;
  const projectCreateResultRef = projectCreateResult;
  const setProjectCreateResultRef = setProjectCreateResult;
  const projectDataRef = project.data;
  const projectMetadataRef = project.data.metadata as Record<string, unknown> | undefined;

  const selectedProjectForPlanReview = useMemo(() => {
    return selectedProjectIdRef &&
      !project.fromFallback &&
      projectDataRef.id === selectedProjectIdRef
      ? projectDataRef
      : null;
  }, [selectedProjectIdRef, project.fromFallback, projectDataRef.id, projectDataRef]);

  const selectedProjectMetadata = useMemo(() => {
    return selectedProjectForPlanReview?.metadata as Record<string, unknown> | undefined;
  }, [selectedProjectForPlanReview]);

  const projectDiagnostics = useMemo(() => {
    if (projectCreateResultRef?.project_id === selectedProjectIdRef) {
      return projectCreateResultRef.diagnostics;
    }
    const d = selectedProjectMetadata?.diagnostics;
    return d && typeof d === "object" ? (d as Record<string, unknown>) : {};
  }, [projectCreateResultRef, selectedProjectIdRef, selectedProjectMetadata]);

  const projectInventory = useMemo(
    () => buildProjectInventory(projectDataRef, overview.data, projectDiagnostics),
    [projectDataRef, overview.data, projectDiagnostics],
  );

  const sequenceOptions = useMemo(() => {
    return Array.from(new Set([...projectDataRef.sequences, ...imageSources.data.sequences]));
  }, [imageSources.data.sequences, projectDataRef.sequences]);

  const selectedImageSource = useMemo(() => {
    const manifest = imageSources.data.manifest ?? [];
    return (
      manifest.find(
        (item) => item.subject_id === selectedSubjectId && item.sequence === sequence,
      ) ??
      manifest.find((item) => item.subject_id === selectedSubjectId) ??
      null
    );
  }, [imageSources.data.manifest, selectedSubjectId, sequence]);

  useEffect(() => {
    const subjects = imageSources.data.subjects;
    if (!subjects.length) return;
    if (!selectedSubjectId || !subjects.some((item) => item.subject_id === selectedSubjectId)) {
      setSelectedSubjectId(subjects[0].subject_id);
    }
  }, [imageSources.data.subjects, selectedSubjectId]);

  useEffect(() => {
    setSliceIndex(null);
  }, [projectDataRef.id, selectedSubjectId, sequence, plane]);

  const handleUploadData = useCallback(async () => {
    setProjectCreateError("");
    setProjectCreateResultRef(null);
    let selectedPath: string | null = null;
    try {
      if (window.medimage?.selectDirectory) {
        selectedPath = await window.medimage.selectDirectory();
      } else {
        selectedPath = window.prompt("Enter a local BIDS / rawdata directory path");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setProjectCreateError(message);
      return;
    }
    if (!selectedPath?.trim()) return;

    setProjectCreateLoading(true);
    try {
      const uploadBaseUrl = await getApiBaseUrl();
      const requestedProjectName = uniqueProjectName(
        directoryBasename(selectedPath),
        projectsRef.data,
      );
      let effectiveProjectName = uniqueProjectName(requestedProjectName, projectsRef.data);
      const createWithName = (name: string) =>
        createProjectFromDirectory(uploadBaseUrl, {
          project_name: name,
          rawdata_dir: selectedPath.trim(),
          copy_mode: "reference",
          run_inspection: true,
          overwrite: false,
        });
      let result: ProjectCreateResponse;
      try {
        result = await createWithName(effectiveProjectName);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        if (!isProjectNameConflict(message)) throw err;
        effectiveProjectName = uniqueProjectName(
          `${requestedProjectName} ${new Date().toISOString().slice(0, 10)}`,
          projectsRef.data,
        );
        result = await createWithName(effectiveProjectName);
      }
      const refreshedProjects = await projectsRef.reload();
      const listSource = refreshedProjects ?? projectsRef.data;
      projectsRef.setData(mergeCreatedProjectIntoList(result, listSource));
      setSelectedProjectIdRef(result.project_id);
      setSelectedSubjectId(null);
      setSliceIndex(null);
      setProjectCreateResultRef(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setProjectCreateError(message);
    } finally {
      setProjectCreateLoading(false);
    }
  }, [projectsRef, setSelectedProjectIdRef]);

  const handleDeleteProject = useCallback(
    async (projectId: string, projectName: string) => {
      if (projectCreateLoading) return;
      const confirmed = window.confirm(
        `Remove "${projectName}" from Recent projects? This will not delete rawdata or project files.`,
      );
      if (!confirmed) return;

      setProjectCreateLoading(true);
      try {
        await deleteProject(projectId);
        const remaining = projectsRef.data.filter((item) => item.id !== projectId);
        projectsRef.setData(remaining);
        if (selectedProjectIdRef === projectId) {
          setSelectedProjectIdRef(remaining[0]?.id ?? null);
          setSelectedSubjectId(null);
          setSliceIndex(null);
          setProjectCreateResultRef(null);
        }
        const refreshedProjects = await projectsRef.reload();
        const latest = (refreshedProjects ?? remaining).filter((item) => item.id !== projectId);
        projectsRef.setData(latest);
        if (selectedProjectIdRef === projectId) {
          setSelectedProjectIdRef(latest[0]?.id ?? null);
        }
      } finally {
        setProjectCreateLoading(false);
      }
    },
    [projectCreateLoading, projectsRef, selectedProjectIdRef, setSelectedProjectIdRef],
  );

  return {
    projects: { data: projects.data, loading: projects.loading, error: projects.error },
    projectsLoading: projects.loading,
    projectsError: projects.error,
    reloadProjects: projects.reload,
    project: project.data,
    projectFromFallback: project.fromFallback,
    projectInventory: buildProjectInventory(projectDataRef, overview.data, projectDiagnostics),
    overview: overview.data,
    overviewLoading: overview.loading,
    overviewError: overview.error,
    projectDiagnostics,
    dataset: dataset.data,
    model: model.data,
    selectedProjectId,
    setSelectedProjectId,
    selectedProjectForPlanReview,
    selectedProjectMetadata,
    sequence,
    setSequence,
    selectedSubjectId,
    setSelectedSubjectId,
    plane,
    setPlane,
    sliceIndex,
    setSliceIndex,
    sequenceOptions,
    imageSources: imageSources.data,
    imageValidation: imageValidation.data,
    imagePreview: imagePreview.data,
    selectedImageSource,
    imagePreviewLoading: imagePreview.loading,
    projectCreateLoading,
    projectCreateError,
    projectCreateResult,
    setProjectCreateResult,
    setProjectCreateError,
    handleUploadData,
    handleDeleteProject,
  };
}

function directoryBasename(path: string): string {
  return path.replace(/\\/g, "/").split("/").filter(Boolean).pop() ?? path;
}
