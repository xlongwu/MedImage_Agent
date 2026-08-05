import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getProjectRun,
  getProjectRunStateTimeline,
  listProjectRunArtifacts,
  listProjectRunEvents,
  listProjectRunLinks,
  listProjectRunLogs,
} from "../projectRuns";

function response(body: string): Response {
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(body),
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("project-scoped run history API", () => {
  it("encodes project and run ids for every persisted run evidence endpoint", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response('{"ok":true}'));
    vi.stubGlobal("fetch", fetchMock);

    await getProjectRun("http://api", "project / 1", "run / 1");
    await listProjectRunEvents("http://api", "project / 1", "run / 1");
    await listProjectRunLogs("http://api", "project / 1", "run / 1", {
      includeContent: true,
      maxBytes: 20000,
    });
    await listProjectRunArtifacts("http://api", "project / 1", "run / 1");
    await getProjectRunStateTimeline("http://api", "project / 1", "run / 1");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://api/api/projects/project%20%2F%201/runs/run%20%2F%201",
      "http://api/api/projects/project%20%2F%201/runs/run%20%2F%201/events",
      "http://api/api/projects/project%20%2F%201/runs/run%20%2F%201/logs?max_bytes=20000&include_content=true",
      "http://api/api/projects/project%20%2F%201/runs/run%20%2F%201/artifacts",
      "http://api/api/projects/project%20%2F%201/runs/run%20%2F%201/state-timeline",
    ]);
  });

  it("lists only the selected project's run links and encodes reviewed plan filters", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(response('{"ok":true,"project_id":"project / 1","runs":[]}'));
    vi.stubGlobal("fetch", fetchMock);

    await listProjectRunLinks("http://api", "project / 1", "plan +/=");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/api/projects/project%20%2F%201/runs?reviewed_plan_id=plan%20%2B%2F%3D",
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });
});
