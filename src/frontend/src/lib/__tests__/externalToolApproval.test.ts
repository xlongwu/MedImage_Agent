import { describe, expect, it } from "vitest";

import {
  detectNativePreprocNodes,
  isNativePreprocApprovalComplete,
} from "../externalToolApproval";

describe("native preprocessing approval helpers", () => {
  it("detects native full preprocessing execute nodes", () => {
    const requirement = detectNativePreprocNodes({
      pipeline_id: "native_full_preprocessing",
      nodes: [
        { id: "data_inspection", backend: "python" },
        { id: "native_preproc_full_execute", backend: "native_python" },
      ],
    });

    expect(requirement.required).toBe(true);
    expect(requirement.nodeIds).toEqual(["native_preproc_full_execute"]);
  });

  it("requires all native preprocessing acknowledgements", () => {
    const requirement = {
      required: true,
      nodeIds: ["native_preproc_full_execute"],
    };

    expect(
      isNativePreprocApprovalComplete(requirement, {
        nativePreprocessingAcknowledgement: true,
        noExternalToolsConfirmed: true,
        rawdataReadOnlyConfirmed: true,
        riskAcknowledgement: true,
        subjectScopeConfirmed: false,
      }),
    ).toBe(false);

    expect(
      isNativePreprocApprovalComplete(requirement, {
        nativePreprocessingAcknowledgement: true,
        noExternalToolsConfirmed: true,
        rawdataReadOnlyConfirmed: true,
        riskAcknowledgement: true,
        subjectScopeConfirmed: true,
      }),
    ).toBe(true);
  });
});
