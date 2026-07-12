import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getLatestRsfmriReportExport,
  getLatestRsfmriReportValidation,
  listRsfmriReportExports,
  listRsfmriReportValidations,
  runRsfmriReportExport,
  runRsfmriReportValidation,
} from "../rsfmri";

function response(body: string, ok = true): Response {
  return {
    ok,
    text: () => Promise.resolve(body),
  } as Response;
}

function mockFetch() {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue(response('{"ok":true}'));
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rs-fMRI report package API", () => {
  it("uses the current report export endpoints", async () => {
    const fetchMock = mockFetch();
    const payload = { project_config_path: "project.yaml", pipeline_path: "pipeline.yaml" };

    await getLatestRsfmriReportExport("http://api");
    await listRsfmriReportExports("http://api");
    await runRsfmriReportExport("http://api", payload);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api/api/rsfmri/report-exports/latest",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api/api/rsfmri/report-exports",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api/api/rsfmri/report-export",
      expect.objectContaining({
        body: JSON.stringify(payload),
        method: "POST",
      }),
    );
  });

  it("uses the current report validation endpoints", async () => {
    const fetchMock = mockFetch();
    const payload = { project_config_path: "project.yaml", pipeline_path: "validator.yaml" };

    await getLatestRsfmriReportValidation("http://api");
    await listRsfmriReportValidations("http://api");
    await runRsfmriReportValidation("http://api", payload);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api/api/rsfmri/report-validations/latest",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api/api/rsfmri/report-validations",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api/api/rsfmri/report-validation",
      expect.objectContaining({
        body: JSON.stringify(payload),
        method: "POST",
      }),
    );
  });
});
