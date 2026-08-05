import { describe, expect, it, vi } from "vitest";

import * as preprocessingApi from "../preprocessing";
import { requestJson } from "../legacyCore";

vi.mock("../legacyCore", () => ({
  requestJson: vi.fn(),
}));

describe("Preprocessing API", () => {
  it("does not export wrappers for backend-rejected legacy execution routes", () => {
    expect(preprocessingApi).not.toHaveProperty("executeReviewedPreprocessingPipeline");
    expect(preprocessingApi).not.toHaveProperty("executeNativeFullPreprocessing");
    expect(preprocessingApi).not.toHaveProperty("submitNativeFullPreprocessing");
  });

  it("keeps native dry-run available without dispatching execution", async () => {
    vi.mocked(requestJson).mockResolvedValueOnce({ status: "planned" });

    await preprocessingApi.runNativeFullPreprocessingDryRun("http://localhost", "project-1", {
      run_id: "pp-demo",
    });

    expect(requestJson).toHaveBeenCalledWith(
      "http://localhost",
      "/api/projects/project-1/preprocessing/native/full/dry-run",
      {
        method: "POST",
        body: JSON.stringify({ run_id: "pp-demo" }),
      },
    );
  });
});
