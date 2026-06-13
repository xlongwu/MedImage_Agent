import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAsyncResource } from "../useAsyncResource";

describe("useAsyncResource", () => {
  it("returns fallback and loading=true initially", () => {
    const loader = vi.fn(() => Promise.resolve("loaded"));
    const { result } = renderHook(() => useAsyncResource(loader, "fallback", []));

    expect(result.current.data).toBe("fallback");
    expect(result.current.loading).toBe(true);
    expect(result.current.fromFallback).toBe(true);
  });

  it("returns resolved data after completion", async () => {
    const loader = vi.fn(() => Promise.resolve("loaded"));
    const { result } = renderHook(() => useAsyncResource(loader, "fallback", []));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBe("loaded");
    expect(result.current.error).toBe("");
    expect(result.current.fromFallback).toBe(false);
  });

  it("returns fallback and error on rejection", async () => {
    const loader = vi.fn(() => Promise.reject(new Error("boom")));
    const { result } = renderHook(() => useAsyncResource(loader, "fallback", []));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBe("fallback");
    expect(result.current.error).toBe("boom");
    expect(result.current.fromFallback).toBe(true);
  });

  it("re-fetches when deps change", async () => {
    const loader = vi.fn((id: string) => Promise.resolve(`loaded-${id}`));
    const { result, rerender } = renderHook(
      ({ id }) => useAsyncResource(() => loader(id), "fallback", [id]),
      { initialProps: { id: "a" } },
    );

    await waitFor(() => expect(result.current.data).toBe("loaded-a"));
    rerender({ id: "b" });
    await waitFor(() => expect(result.current.data).toBe("loaded-b"));

    expect(loader).toHaveBeenCalledTimes(2);
  });

  it("does not re-fetch when deps are unchanged", async () => {
    const loader = vi.fn(() => Promise.resolve("loaded"));
    const { result, rerender } = renderHook(
      ({ label }) => useAsyncResource(loader, label, []),
      { initialProps: { label: "fallback-a" } },
    );

    await waitFor(() => expect(result.current.data).toBe("loaded"));
    rerender({ label: "fallback-b" });

    expect(loader).toHaveBeenCalledTimes(1);
  });

  it("handles null loader gracefully", async () => {
    const { result } = renderHook(() => useAsyncResource<string>(null, "fallback", []));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBe("fallback");
    expect(result.current.error).toBe("");
    expect(result.current.fromFallback).toBe(true);
  });

  it("reload returns the loaded value", async () => {
    const loader = vi.fn(() => Promise.resolve("loaded"));
    const { result } = renderHook(() => useAsyncResource(loader, "fallback", []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    await expect(result.current.reload()).resolves.toBe("loaded");
  });

  it("exposes setData for local optimistic updates", async () => {
    const loader = vi.fn(() => Promise.resolve("loaded"));
    const { result } = renderHook(() => useAsyncResource(loader, "fallback", []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.setData("manual"));

    expect(result.current.data).toBe("manual");
  });
});
