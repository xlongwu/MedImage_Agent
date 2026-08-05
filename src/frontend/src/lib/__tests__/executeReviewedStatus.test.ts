import { describe, expect, it } from "vitest";

import { describeExecuteReviewedStatus } from "../executeReviewedStatus";

describe("describeExecuteReviewedStatus", () => {
  it("maps missing Goal Contract review to a safe actionable status", () => {
    expect(describeExecuteReviewedStatus("REVIEWED_PLAN_NEEDS_GOAL_REVIEW")).toEqual(
      expect.objectContaining({
        status: "REVIEWED_PLAN_NEEDS_GOAL_REVIEW",
        title: "Goal Contract review required",
        severity: "warning",
        canRetryDryRun: false,
        canAttemptExecute: false,
      }),
    );
  });

  it("directs Agent-owned reviewed plans back to their authoritative task", () => {
    expect(describeExecuteReviewedStatus("AGENT_LIFECYCLE_ID_REQUIRED")).toEqual(
      expect.objectContaining({
        title: "Open this plan from its Agent Task",
        canRetryDryRun: true,
        canAttemptExecute: false,
      }),
    );
  });
});
