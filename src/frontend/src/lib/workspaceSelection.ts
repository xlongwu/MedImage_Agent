import type { ImagePlane } from "./types/image";
import type { EvidenceLevel } from "./evidence";

export type PlanNodeSelection = {
  backend: string;
  detail: string;
  id: string;
  name: string;
  risk: string;
};

export type ArtifactSelection = {
  evidenceLevel: EvidenceLevel;
  name: string;
  path: string;
  previewType: string;
  runId: string | null;
  stage: string;
  subject: string;
};

export type DataSeriesSelection = {
  evidenceLevel: EvidenceLevel;
  sourceKind: "project_summary" | "source_summary" | "mapping_preview";
  status: string;
  subject: string;
  subjectDetail: string;
  series: string;
  seriesDetail: string;
  warnings: string[];
};

export type WorkspaceSelectionContext = {
  artifact: ArtifactSelection | null;
  dataSeries: DataSeriesSelection | null;
  image: {
    plane: ImagePlane;
    series: string | null;
    source: string | null;
    subjectId: string | null;
  };
  planNode: PlanNodeSelection | null;
  run: {
    id: string | null;
    name: string | null;
    pipeline: string | null;
    status: string | null;
  };
};
