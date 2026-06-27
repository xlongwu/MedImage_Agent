import { getStudyOverview } from "../lib/api";
import { fallbackOverview } from "../lib/mockData";
import type { StudyOverview } from "../lib/types/project";
import { useAsyncResource } from "./useAsyncResource";

export function useProjectOverview(studyId: string | null) {
  return useAsyncResource<StudyOverview>(
    studyId ? () => getStudyOverview(studyId) : null,
    fallbackOverview,
    [studyId],
  );
}
