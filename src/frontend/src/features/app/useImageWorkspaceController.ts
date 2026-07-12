import { useCallback, useMemo, useState } from "react";

import { useImagePreview } from "../../hooks/useImagePreview";
import { useImageSources } from "../../hooks/useImageSources";
import { useImageValidation } from "../../hooks/useImageValidation";
import type { ImagePlane } from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";

export function useImageWorkspaceController(
  activeProjectId: string | null,
  project: ProjectDetail,
) {
  const [requestedSequence, setSequence] = useState("T1");
  const [plane, setPlane] = useState<ImagePlane>("axial");
  const [sliceSelection, setSliceSelection] = useState<{ key: string; value: number | null }>({
    key: "",
    value: null,
  });
  const [requestedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const imageSources = useImageSources(activeProjectId);
  const imageValidation = useImageValidation(activeProjectId);
  const sequenceOptions = useMemo(
    () => Array.from(new Set([...project.sequences, ...imageSources.data.sequences])),
    [imageSources.data.sequences, project.sequences],
  );
  const sequence = sequenceOptions.includes(requestedSequence)
    ? requestedSequence
    : (sequenceOptions[0] ?? requestedSequence);
  const selectedSubjectId = imageSources.data.subjects.some(
    (item) => item.subject_id === requestedSubjectId,
  )
    ? requestedSubjectId
    : (imageSources.data.subjects[0]?.subject_id ?? null);
  const sliceKey = `${project.id}:${selectedSubjectId ?? ""}:${sequence}:${plane}`;
  const sliceIndex = sliceSelection.key === sliceKey ? sliceSelection.value : null;
  const imagePreview = useImagePreview(
    activeProjectId,
    sequence,
    selectedSubjectId,
    sliceIndex,
    plane,
  );
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

  const setSliceIndex = useCallback(
    (value: number | null) => setSliceSelection({ key: sliceKey, value }),
    [sliceKey],
  );

  return {
    imagePreview,
    imageSources,
    imageValidation,
    plane,
    selectedImageSource,
    selectedSubjectId,
    sequence,
    sequenceOptions,
    setPlane,
    setSelectedSubjectId,
    setSequence,
    setSliceIndex,
    sliceIndex,
  };
}
