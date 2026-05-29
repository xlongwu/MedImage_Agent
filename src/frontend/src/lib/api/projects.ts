import { getJson } from "./client";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "../types/project";

export function getProjects(): Promise<ProjectSummary[]> {
  return getJson<ProjectSummary[]>("/api/projects");
}

export function getProject(projectId: string): Promise<ProjectDetail> {
  return getJson<ProjectDetail>(`/api/projects/${encodeURIComponent(projectId)}`);
}

export function getStudyOverview(studyId: string): Promise<StudyOverview> {
  return getJson<StudyOverview>(`/api/studies/${encodeURIComponent(studyId)}/overview`);
}

