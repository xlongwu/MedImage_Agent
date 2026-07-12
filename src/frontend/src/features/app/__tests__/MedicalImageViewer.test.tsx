import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import type { ImagePreview, ImageSources, ImageValidationReport } from "../../../lib/types/image";
import type { ProjectDetail } from "../../../lib/types/project";
import { MedicalImageViewer } from "../MedicalImageViewer";

const project: ProjectDetail = {
  id: "project-1",
  name: "Demo Project",
  study_id: "study-1",
  modality: "rs-fMRI",
  created_date: "2026-06-24",
  subjects_count: 1,
  current_pipeline_id: "pipeline-1",
  sequences: ["BOLD"],
  scans_count: 1,
  total_size: "1 GB",
  current_model_id: "model-1",
  metadata: {},
};

const imageSources: ImageSources = {
  project_id: "project-1",
  subjects: [
    {
      subject_id: "sub-01",
      sequences: ["BOLD"],
      files: { BOLD: "sub-01/func/bold.nii.gz" },
    },
  ],
  sequences: ["BOLD"],
  roots: ["bids"],
  manifest: [
    {
      subject_id: "sub-01",
      sequence: "BOLD",
      file_path: "D:/study/sub-01/func/bold.nii.gz",
      relative_path: "sub-01/func/bold.nii.gz",
      format: "nifti",
      dimensions: [64, 64, 32, 180],
      voxel_spacing: [3, 3, 3],
      plane_slice_counts: { axial: 32, coronal: 64, sagittal: 64 },
      warnings: [],
    },
  ],
};

const validation: ImageValidationReport = {
  ok: true,
  project_id: "project-1",
  status: "pass",
  checked_at: "2026-06-24T08:00:00Z",
  source_count: 1,
  subject_count: 1,
  sequence_count: 1,
  expected_sequences: ["BOLD"],
  issues: [],
};

function renderViewer(
  preview: ImagePreview | null,
  dataState: "converted_bids" | "raw_dicom" = "converted_bids",
  overrides: {
    loading?: boolean;
    onSliceChange?: (sliceIndex: number) => void;
    validation?: ImageValidationReport;
    locale?: "en" | "zh-CN";
  } = {},
) {
  const onSliceChange = overrides.onSliceChange ?? vi.fn();

  render(
    <I18nProvider locale={overrides.locale ?? "en"}>
      <MedicalImageViewer
        dataState={dataState}
        imageSources={imageSources}
        loading={overrides.loading ?? false}
        onPlaneChange={vi.fn()}
        onSequenceChange={vi.fn()}
        onSliceChange={onSliceChange}
        onSubjectChange={vi.fn()}
        plane="axial"
        preview={preview}
        project={project}
        sequence="BOLD"
        sequenceOptions={["BOLD"]}
        sourceFile={imageSources.manifest?.[0] ?? null}
        subjectId="sub-01"
        validation={overrides.validation ?? validation}
      />
    </I18nProvider>,
  );

  return { onSliceChange };
}

describe("MedicalImageViewer", () => {
  it("does not crash when optional validation details are absent", () => {
    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
        source: "nifti",
        slice_count: 32,
        slice_index: 8,
      },
      "converted_bids",
      {
        validation: {
          ...validation,
          issues: undefined as unknown as ImageValidationReport["issues"],
        },
      },
    );

    expect(screen.getByText(/Validation pass/)).toBeInTheDocument();
  });

  it("shows a Raw DICOM empty state with conversion guidance instead of an image canvas", () => {
    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: null,
        message: "Raw DICOM preview disabled",
        source: "dicom",
        slice_count: 0,
        slice_index: 0,
      },
      "raw_dicom",
    );

    expect(screen.getByLabelText("Image viewer empty state")).toHaveTextContent(
      "Complete DICOM conversion to enable NIfTI preview",
    );
    expect(screen.getByLabelText("Image viewer empty state")).toHaveTextContent(
      "Project state: raw_dicom",
    );
    expect(screen.getByText("Next: Open Data & Conversion")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open data/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows an explicit empty state instead of synthetic imagery without a preview URL", () => {
    renderViewer({
      project_id: "project-1",
      subject_id: "sub-01",
      sequence: "BOLD",
      preview_url: null,
      message: "Preview not registered",
      source: "nifti",
      slice_count: 32,
      slice_index: 0,
    });

    expect(screen.getByLabelText("Image viewer empty state")).toHaveTextContent(
      "No image preview is available",
    );
    expect(screen.queryByLabelText("Synthetic MRI scan preview")).not.toBeInTheDocument();
    expect(screen.queryByText(/demo \/ not project data/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("handles a null preview without rendering fallback medical imagery", () => {
    renderViewer(null);

    expect(screen.getByLabelText("Image viewer empty state")).toHaveTextContent(
      "No image preview is available",
    );
    expect(screen.queryByLabelText("Synthetic MRI scan preview")).not.toBeInTheDocument();
  });

  it("renders the image preview only when a real preview URL is present", () => {
    renderViewer({
      project_id: "project-1",
      subject_id: "sub-01",
      sequence: "BOLD",
      preview_url: "/api/projects/project-1/preview.png",
      message: "Preview ready",
      source: "nifti",
      source_path: "sub-01/func/bold.nii.gz",
      dimensions: [64, 64, 32, 180],
      slice_count: 32,
      slice_index: 4,
    });

    expect(screen.getByRole("img", { name: /medical image preview/i })).toHaveAttribute(
      "src",
      "/api/projects/project-1/preview.png",
    );
    expect(screen.queryByLabelText("Synthetic MRI scan preview")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Viewer status")).toHaveTextContent("5 / 32");
  });

  it("shows a visible loading state and pauses slice shortcuts while previews change", async () => {
    const user = userEvent.setup();
    const onSliceChange = vi.fn();

    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
        source: "nifti",
        source_path: "sub-01/func/bold.nii.gz",
        dimensions: [64, 64, 32, 180],
        slice_count: 32,
        slice_index: 4,
      },
      "converted_bids",
      { loading: true, onSliceChange },
    );

    const viewer = screen.getByRole("group", { name: /loading image preview/i });

    expect(viewer).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status")).toHaveTextContent("Loading image preview");
    expect(screen.getByLabelText("Viewer status")).toHaveTextContent("Slice");

    await user.click(viewer);
    await user.keyboard("{ArrowRight}");

    expect(onSliceChange).not.toHaveBeenCalled();
  });

  it("lets keyboard users request adjacent, first, and last slices on a real preview", async () => {
    const user = userEvent.setup();
    const onSliceChange = vi.fn();

    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
        source: "nifti",
        source_path: "sub-01/func/bold.nii.gz",
        dimensions: [64, 64, 32, 180],
        slice_count: 32,
        slice_index: 4,
      },
      "converted_bids",
      { onSliceChange },
    );

    const viewer = screen.getByRole("group", { name: /medical image viewer/i });
    await user.click(viewer);
    expect(viewer).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    expect(onSliceChange).toHaveBeenLastCalledWith(5);

    await user.keyboard("{Home}");
    expect(onSliceChange).toHaveBeenLastCalledWith(0);

    await user.keyboard("{End}");
    expect(onSliceChange).toHaveBeenLastCalledWith(31);
  });

  it("does not request out-of-bounds slices from keyboard navigation", async () => {
    const user = userEvent.setup();
    const onSliceChange = vi.fn();

    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
        source: "nifti",
        source_path: "sub-01/func/bold.nii.gz",
        dimensions: [64, 64, 32, 180],
        slice_count: 32,
        slice_index: 31,
      },
      "converted_bids",
      { onSliceChange },
    );

    const viewer = screen.getByRole("group", { name: /medical image viewer/i });
    await user.click(viewer);
    await user.keyboard("{ArrowRight}");

    expect(onSliceChange).not.toHaveBeenCalled();
  });

  it("lets keyboard users leave the image viewer focus with Escape", async () => {
    const user = userEvent.setup();

    renderViewer({
      project_id: "project-1",
      subject_id: "sub-01",
      sequence: "BOLD",
      preview_url: "/api/projects/project-1/preview.png",
      message: "Preview ready",
      source: "nifti",
      source_path: "sub-01/func/bold.nii.gz",
      dimensions: [64, 64, 32, 180],
      slice_count: 32,
      slice_index: 4,
    });

    const viewer = screen.getByRole("group", { name: /medical image viewer/i });
    await user.click(viewer);
    expect(viewer).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(viewer).not.toHaveFocus();
  });

  it("renders the verified preview workflow in Chinese", () => {
    renderViewer(
      {
        project_id: "project-1",
        subject_id: "sub-01",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
        source: "nifti",
        source_path: "sub-01/func/bold.nii.gz",
        dimensions: [64, 64, 32, 180],
        slice_count: 32,
        slice_index: 4,
      },
      "converted_bids",
      { locale: "zh-CN" },
    );

    expect(screen.getByRole("tablist", { name: "解剖平面" })).toBeInTheDocument();
    expect(screen.getByLabelText("查看器状态")).toHaveTextContent("层面");
    expect(screen.getByLabelText("影像元数据与验证")).toHaveTextContent("检查器");
    expect(screen.getByRole("toolbar", { name: "查看器画布工具" })).toBeInTheDocument();
  });
});
