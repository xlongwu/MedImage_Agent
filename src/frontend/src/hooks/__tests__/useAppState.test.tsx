import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useAppState } from "../useAppState";

const THEME_STORAGE_KEY = "medimage.themePreference";

describe("useAppState", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
  });

  it("applies the light theme by default", async () => {
    const { result } = renderHook(() => useAppState());

    expect(result.current.themePreference).toBe("light");
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("light");
    });
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("reads a persisted dark theme preference", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");

    const { result } = renderHook(() => useAppState());

    expect(result.current.themePreference).toBe("dark");
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("dark");
    });
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("updates the document theme when the preference changes", async () => {
    const { result } = renderHook(() => useAppState());

    act(() => result.current.setThemePreference("dark"));

    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("dark");
    });
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });
});
