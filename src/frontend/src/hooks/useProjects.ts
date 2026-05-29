import { getProject, getProjects } from "../lib/api";
import { fallbackProjectDetail, fallbackProjects } from "../lib/mockData";
import type { ProjectDetail, ProjectSummary } from "../lib/types/project";
import { useAsyncResource } from "./useAsyncResource";

export function useProjects() {
  return useAsyncResource<ProjectSummary[]>(getProjects, fallbackProjects, []);
}

export function useProject(projectId: string | null) {
  return useAsyncResource<ProjectDetail>(
    () => (projectId ? getProject(projectId) : Promise.resolve(fallbackProjectDetail)),
    fallbackProjectDetail,
    [projectId]
  );
}

