import { useCallback, useState } from "react";

import type { AppLocation, LegacyWorkspace, ProjectWorkspace } from "./workspaceModel";
import { legacyLocationForProject, locationForProject } from "./workspaceModel";

export function useWorkspaceNavigation() {
  const [location, setLocation] = useState<AppLocation>({ kind: "projects" });

  const openProjects = useCallback(() => setLocation({ kind: "projects" }), []);
  const openProject = useCallback(
    (projectId: string) => setLocation(locationForProject(projectId)),
    [],
  );
  const openWorkspace = useCallback((projectId: string, workspace: ProjectWorkspace) => {
    setLocation({ kind: "project", projectId, workspace });
  }, []);
  const openLegacyWorkspace = useCallback((projectId: string, workspace: LegacyWorkspace) => {
    setLocation(legacyLocationForProject(projectId, workspace));
  }, []);

  return {
    location,
    openLegacyWorkspace,
    openProject,
    openProjects,
    openWorkspace,
    setLocation,
  };
}
