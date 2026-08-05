// @ts-expect-error Vitest executes this contract test in Node.
import { readFileSync } from "node:fs";
// @ts-expect-error Vitest executes this contract test in Node.
import { dirname, resolve } from "node:path";
// @ts-expect-error Vitest executes this contract test in Node.
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const workspaceDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const agentDir = resolve(workspaceDir, "../agent");

function readWorkspaceStyle(name: string): string {
  return readFileSync(resolve(workspaceDir, name), "utf8");
}

describe("workspace row-balance contract", () => {
  it("stretches shared panel rows and promotes a lone panel to the full row", () => {
    const source = readWorkspaceStyle("WorkspaceLayout.module.css");

    expect(source).toMatch(/\.panelGrid\s*{[\s\S]*?align-items:\s*stretch;/);
    expect(source).toMatch(
      /\.panelGrid\s*>\s*div:only-child\s*{[\s\S]*?grid-column:\s*1\s*\/\s*-1;/,
    );
    expect(source).toMatch(/\.panelGrid\s*>\s*div\s*>\s*\*\s*{[\s\S]*?flex:\s*1\s+1\s+auto;/);
  });

  it("keeps the primary desktop workspaces on equal-height rows", () => {
    const workspaceStyles = [
      "OverviewWorkspace.module.css",
      "DataConversionWorkspace.module.css",
      "PlanWorkspace.module.css",
      "PreprocessingWorkspace.module.css",
      "RunsWorkspace.module.css",
      "QCReportsWorkspace.module.css",
      "ResultsWorkspace.module.css",
      "SettingsEnvironmentWorkspace.module.css",
    ];

    for (const name of workspaceStyles) {
      expect(readWorkspaceStyle(name), name).toContain("align-items: stretch;");
    }

    const agent = readFileSync(resolve(agentDir, "AgentWorkspace.module.css"), "utf8");
    expect(agent).toMatch(/\.projectSummary\s*{[\s\S]*?align-items:\s*stretch;/);
  });

  it("uses explicit row groupings where automatic placement previously left orphan cards", () => {
    const plan = readWorkspaceStyle("PlanWorkspace.module.css");
    const preprocessing = readWorkspaceStyle("PreprocessingWorkspace.module.css");
    const qualityControl = readWorkspaceStyle("QCReportsWorkspace.module.css");
    const settings = readWorkspaceStyle("SettingsEnvironmentWorkspace.module.css");

    expect(plan).toContain('grid-template-areas: "outline graph inspector"');
    expect(preprocessing).toMatch(/\.handoffCard\s*{[\s\S]*?order:\s*2;/);
    expect(preprocessing).toMatch(/\.executionGateCard\s*{[\s\S]*?order:\s*3;/);
    expect(qualityControl).toMatch(/\.summaryCard\s*{[\s\S]*?grid-column:\s*span\s+7;/);
    expect(qualityControl).toMatch(/\.outlierCard\s*{[\s\S]*?grid-column:\s*span\s+5;/);
    expect(qualityControl).toMatch(
      /\.comparisonCard,[\s\S]*?\.visualSpecCard\s*{[\s\S]*?grid-column:\s*span\s+4;/,
    );
    expect(settings).not.toContain("grid-row: span 2;");
  });
});
