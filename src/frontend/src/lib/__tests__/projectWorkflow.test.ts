import { describe, expect, it } from "vitest";
import {
  buildProjectInventory,
  deriveDefaultWorkflowRoute,
  deriveDefaultWorkflowTab,
  deriveProjectWorkflowState,
  directoryBasename,
  isProjectNameConflict,
  mergeCreatedProjectIntoList,
  uniqueProjectName,
} from "../projectWorkflow";
import type { ProjectCreateResponse } from "../../types";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "../types/project";

function project(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: "project-1",
    name: "Demo Project",
    study_id: "study-1",
    modality: "rs-fMRI",
    created_date: "2026-06-13",
    subjects_count: 0,
    current_pipeline_id: "not-selected",
    sequences: [],
    scans_count: 0,
    total_size: "0 B",
    current_model_id: "none",
    ...overrides,
  };
}

function overview(overrides: Partial<StudyOverview> = {}): StudyOverview {
  return {
    project_id: "project-1",
    study_id: "study-1",
    study_name: "Demo Study",
    modality: "rs-fMRI",
    sequences: [],
    subjects: 0,
    scans: 0,
    total_size: "0 B",
    date: "2026-06-13",
    ...overrides,
  };
}

function summary(id: string, name: string): ProjectSummary {
  return {
    id,
    name,
    study_id: id,
    modality: "rs-fMRI",
    created_date: "2026-06-13",
    subjects_count: 1,
    current_pipeline_id: "not-selected",
  };
}

describe("deriveProjectWorkflowState", () => {
  it("returns unknown when project is null", () => {
    expect(deriveProjectWorkflowState(null)).toBe("unknown");
  });

  it("returns empty when no import or imaging evidence exists", () => {
    expect(deriveProjectWorkflowState(project())).toBe("empty");
  });

  it("returns raw_dicom when diagnostics contain DICOM files", () => {
    const state = deriveProjectWorkflowState(
      project({
        metadata: { diagnostics: { dicom_file_count: 24 } },
      }),
    );

    expect(state).toBe("raw_dicom");
  });

  it("returns raw_dicom when readiness warning names raw DICOM layout", () => {
    const state = deriveProjectWorkflowState(project(), {
      warnings: ["DICOM layout detected under FunRaw"],
    });

    expect(state).toBe("raw_dicom");
  });

  it("returns converted_bids when BIDS validation reports NIfTI files", () => {
    const state = deriveProjectWorkflowState(project(), null, {
      nifti_file_count: 12,
      subject_count: 3,
    });

    expect(state).toBe("converted_bids");
  });

  it("returns converted_bids when project has converted subject evidence", () => {
    const state = deriveProjectWorkflowState(project({ subjects_count: 4 }));

    expect(state).toBe("converted_bids");
  });

  it("returns mixed when raw DICOM and converted outputs coexist", () => {
    const state = deriveProjectWorkflowState(
      project({ metadata: { diagnostics: { dicom_series_count: 5 } } }),
      { nifti_file_count: 8, converted_subject_count: 2 },
    );

    expect(state).toBe("mixed");
  });

  it("keeps metadata-only NIfTI inventory from counting as converted data", () => {
    const state = deriveProjectWorkflowState(
      project({
        metadata: {
          diagnostics: {
            nifti_file_count: 0,
            note: "metadata-only inventory",
          },
        },
      }),
    );

    expect(state).toBe("empty");
  });
});

describe("project inventory helpers", () => {
  it("builds inventory for raw DICOM projects", () => {
    const inventory = buildProjectInventory(
      project({ subjects_count: 2 }),
      overview({ dicom_files: 90, dicom_series: 6 }),
      {},
    );

    expect(inventory.dataState).toBe("raw_dicom");
    expect(inventory.hasRawDicom).toBe(true);
    expect(inventory.dicomFileCount).toBe(90);
  });

  it("builds inventory for converted projects", () => {
    const inventory = buildProjectInventory(
      project({ subjects_count: 2 }),
      overview({ subjects: 2 }),
      { nifti_file_count: 12 },
    );

    expect(inventory.dataState).toBe("converted_bids");
    expect(inventory.hasConvertedData).toBe(true);
    expect(inventory.niftiFileCount).toBe(12);
  });

  it("extracts directory basename across separators", () => {
    expect(directoryBasename("D:\\data\\StudyA\\")).toBe("StudyA");
    expect(directoryBasename("/tmp/StudyB")).toBe("StudyB");
  });
});

describe("deriveDefaultWorkflowRoute", () => {
  it("routes raw and empty projects to Data & Conversion", () => {
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "raw_dicom" } })).toBe("data");
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "empty" } })).toBe("data");
  });

  it("routes converted and mixed projects to Preprocessing", () => {
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "converted_bids" } })).toBe(
      "preprocessing",
    );
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "mixed" } })).toBe("preprocessing");
  });

  it("routes running, pending, and failed tasks to Runs before data-state defaults", () => {
    expect(
      deriveDefaultWorkflowRoute({
        inventory: { dataState: "converted_bids" },
        tasks: [{ status: "running" }],
      }),
    ).toEqual({ reason: "active_or_failed_run", tab: "runs" });
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "raw_dicom" }, tasks: [{ status: "pending" }] })).toBe(
      "runs",
    );
    expect(deriveDefaultWorkflowTab({ inventory: { dataState: "empty" }, tasks: [{ status: "failed" }] })).toBe(
      "runs",
    );
  });

  it("routes explicit QC attention to QC after a preprocessing run exists", () => {
    expect(
      deriveDefaultWorkflowRoute({
        diagnostics: { qc_attention_required: true },
        hasPreprocessingRun: true,
        inventory: { dataState: "converted_bids" },
      }),
    ).toEqual({ reason: "qc_attention", tab: "reports" });
  });

  it("keeps converted data in Preprocessing when QC attention is not backed by run evidence", () => {
    expect(
      deriveDefaultWorkflowRoute({
        diagnostics: { qc_attention_required: true },
        hasPreprocessingRun: false,
        inventory: { dataState: "converted_bids" },
      }),
    ).toEqual({ reason: "converted_data", tab: "preprocessing" });
  });
});

describe("uniqueProjectName", () => {
  it("returns original name when there is no conflict", () => {
    expect(uniqueProjectName("New Study", [summary("1", "Old Study")])).toBe("New Study");
  });

  it("appends numeric suffix on first conflict", () => {
    expect(uniqueProjectName("Study", [summary("1", "Study")])).toBe("Study 2");
  });

  it("increments suffix for multiple conflicts", () => {
    const projects = [summary("1", "Study"), summary("2", "Study 2"), summary("3", "Study 3")];
    expect(uniqueProjectName("Study", projects)).toBe("Study 4");
  });
});

describe("project create result helpers", () => {
  it("merges created project at the front and removes stale duplicates", () => {
    const result: ProjectCreateResponse = {
      ok: true,
      project_id: "project-2",
      project_name: "Created",
      project_dir: "outputs/work/Created",
      rawdata_dir: "examples/rawdata",
      project_config_path: "outputs/work/Created/project_config.yaml",
      dataset_index_path: null,
      diagnostics: { subjects_total: 5 },
      warnings: [],
      next_actions: [],
    };

    const merged = mergeCreatedProjectIntoList(result, [
      summary("project-1", "Existing"),
      summary("project-2", "Old Created"),
    ]);

    expect(merged.map((item) => item.id)).toEqual(["project-2", "project-1"]);
    expect(merged[0].subjects_count).toBe(5);
  });

  it("detects project name conflict messages", () => {
    expect(isProjectNameConflict("Project directory already exists")).toBe(true);
    expect(isProjectNameConflict("Set overwrite=true to replace it")).toBe(true);
    expect(isProjectNameConflict("network timeout")).toBe(false);
  });
});
