// @ts-expect-error Vitest executes this contract test in Node.
import { readFileSync, readdirSync } from "node:fs";
// @ts-expect-error Vitest executes this contract test in Node.
import { dirname, extname, resolve } from "node:path";
// @ts-expect-error Vitest executes this contract test in Node.
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const contractFile = fileURLToPath(import.meta.url);
const srcDir = resolve(dirname(contractFile), "../../..");

function readSources(directory = srcDir): Array<{ path: string; source: string }> {
  return readdirSync(directory, { withFileTypes: true }).flatMap(
    (entry: { isDirectory(): boolean; name: string }) => {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) return readSources(path);
      if (![".ts", ".tsx", ".css"].includes(extname(path))) return [];
      return [{ path, source: readFileSync(path, "utf8") }];
    },
  );
}

describe("frontend refactor source contract", () => {
  it("keeps production source independent from the static design folder and external CDNs", () => {
    const offenders = readSources().filter(
      ({ path, source }) =>
        path !== contractFile && /cdn\.jsdelivr|unpkg|medimage-agent-ui-design/.test(source),
    );
    expect(offenders.map(({ path }) => path)).toEqual([]);
  });

  it("keeps feature workspaces off the legacy API aggregation module", () => {
    const featureDir = resolve(srcDir, "features");
    const offenders = readSources(featureDir).filter(
      ({ path, source }) => path !== contractFile && /lib\/api\/legacy/.test(source),
    );
    expect(offenders.map(({ path }) => path)).toEqual([]);
  });

  it("does not hardcode the old v0.6 product label", () => {
    const offenders = readSources().filter(
      ({ path, source }) => path !== contractFile && /["'`]v0\.6["'`]/.test(source),
    );
    expect(offenders.map(({ path }) => path)).toEqual([]);
  });

  it("keeps the legacy DICOM execution panel user-facing copy in the message catalogs", () => {
    const source = readFileSync(
      resolve(srcDir, "components/DicomConversionExecutePanel.tsx"),
      "utf8",
    );
    const hardcodedCopy = [
      "Approve and request conversion",
      "Prepare conversion (unified workflow)",
      "Back to readiness",
      "Conversion partially completed",
      "You are about to execute DICOM-to-NIfTI conversion",
      "MedImage Agent is for research use only",
    ];
    expect(hardcodedCopy.filter((copy) => source.includes(copy))).toEqual([]);
  });

  it("keeps the legacy DICOM review panel user-facing copy in the message catalogs", () => {
    const source = readFileSync(
      resolve(srcDir, "components/DicomConversionReviewPanel.tsx"),
      "utf8",
    );
    const hardcodedCopy = [
      "Real DICOM-to-NIfTI conversion for user data",
      "Check conversion readiness",
      "Save review draft",
      "Show technical details",
      "Real conversion remains disabled in this release",
      "No conversion smoke results have been generated",
    ];
    expect(hardcodedCopy.filter((copy) => source.includes(copy))).toEqual([]);
  });
});
