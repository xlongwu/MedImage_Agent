import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nProvider";
import { getProjectBidsValidation } from "../../lib/api/dicom";
import BidsValidationPanel from "../BidsValidationPanel";

vi.mock("../../lib/api/dicom", () => ({
  getProjectBidsValidation: vi.fn(),
}));

describe("BidsValidationPanel", () => {
  it("renders the App-level validation snapshot without issuing a second scan", () => {
    render(
      <I18nProvider locale="zh-CN">
        <BidsValidationPanel
          baseUrl="http://localhost"
          projectId="project-1"
          projectState="converted_bids"
          validation={{
            loading: false,
            error: "",
            data: {
              ok: true,
              project_id: "project-1",
              status: "pass",
              checked_at: "2026-07-25T00:00:00Z",
              roots: ["D:\\study\\bids"],
              subject_count: 2,
              session_count: 0,
              nifti_file_count: 4,
              sidecar_json_count: 4,
              tsv_file_count: 1,
              issues: [],
              repair_suggestions: [],
              warnings: [],
              errors: [],
              next_actions: [],
            },
          }}
        />
      </I18nProvider>,
    );

    expect(screen.getByText("NIfTI 文件").parentElement).toHaveTextContent("4");
    expect(screen.getByText("已转换受试者").parentElement).toHaveTextContent("2");
    expect(getProjectBidsValidation).not.toHaveBeenCalled();
  });
});
