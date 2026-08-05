import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nProvider";
import type { DicomConversionPreflightResponse } from "../../types";
import DicomConversionExecutePanel from "../DicomConversionExecutePanel";

function preflight(
  overrides: Partial<DicomConversionPreflightResponse> = {},
): DicomConversionPreflightResponse {
  return {
    ok: false,
    project_id: "project-1",
    status: "blocked",
    conversion_disabled_by_default: true,
    conversion_backend: "medimage-native",
    native_converter_available: false,
    native_converter_status: "missing",
    native_converter_version: null,
    native_dependency_versions: {},
    dcm2niix_available: false,
    dcm2niix_status: "disabled",
    dcm2niix_path: null,
    dcm2niix_version: null,
    env_enabled: false,
    missing_env_flags: [],
    approval_required: true,
    audit_required: true,
    output_root_preview: null,
    output_dir_safe: true,
    mapping_count: 1,
    mappings: [],
    command_templates: [],
    warnings: [],
    errors: [],
    blocking_issues: ["Native converter dependencies are unavailable."],
    safety_flags: {
      rawdata_read_only: true,
      output_under_project: true,
      no_shell_string: true,
      command_template_only: true,
      approval_required: true,
      audit_required: true,
      conversion_disabled_by_default: true,
      env_flags_missing: false,
      no_spm_dpabi_matlab: true,
      clinical_use_prohibited: true,
      research_use_only: true,
    },
    ...overrides,
  };
}

function renderPanel(conversionPreflight: DicomConversionPreflightResponse | null) {
  return render(
    <I18nProvider locale="en">
      <DicomConversionExecutePanel
        baseUrl="http://127.0.0.1:8000"
        projectId="project-1"
        conversionRunId="conversion-1"
        readiness={null}
        preflight={conversionPreflight}
      />
    </I18nProvider>,
  );
}

describe("DicomConversionExecutePanel", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_ENABLE_DICOM_EXECUTE_UI", "1");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("shows an early blocking dependency state without an execution action", () => {
    renderPanel(preflight());

    expect(screen.getByRole("status")).toHaveTextContent("Controlled execution only");
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText(/pydicom, nibabel, and numpy/i)).toBeInTheDocument();
    expect(screen.getByText(/dependency check did not pass/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders backend-reported dependency versions without enabling execution", () => {
    renderPanel(
      preflight({
        ok: true,
        status: "ready",
        native_converter_available: true,
        native_converter_status: "available",
        native_converter_version: "1.0",
        native_dependency_versions: {
          pydicom: "3.0.1",
          nibabel: "5.3.2",
          numpy: "2.2.4",
        },
      }),
    );

    expect(screen.getByText("Available")).toBeInTheDocument();
    expect(screen.getByText(/pydicom 3\.0\.1/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("stays hidden when the production feature surface is disabled", () => {
    vi.stubEnv("VITE_ENABLE_DICOM_EXECUTE_UI", "0");

    const { container } = renderPanel(preflight());

    expect(container).toBeEmptyDOMElement();
  });
});
