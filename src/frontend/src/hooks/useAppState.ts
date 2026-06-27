import { useCallback, useEffect, useMemo, useState } from "react";

export type ThemePreference = "light" | "dark";

const THEME_STORAGE_KEY = "medimage.themePreference";
const FALLBACK_THEME: ThemePreference = "light";

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "light" || value === "dark";
}

function readStoredThemePreference(): ThemePreference {
  if (typeof window === "undefined") return FALLBACK_THEME;

  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : FALLBACK_THEME;
  } catch {
    return FALLBACK_THEME;
  }
}

function persistThemePreference(themePreference: ThemePreference): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, themePreference);
  } catch {
    // Theme remains applied for this session even when storage is unavailable.
  }
}

function applyThemePreference(themePreference: ThemePreference): void {
  if (typeof document === "undefined") return;

  document.documentElement.dataset.theme = themePreference;
  document.documentElement.style.colorScheme = themePreference;
}

export function useAppState() {
  const [themePreference, setThemePreferenceState] =
    useState<ThemePreference>(readStoredThemePreference);

  useEffect(() => {
    applyThemePreference(themePreference);
    persistThemePreference(themePreference);
  }, [themePreference]);

  const setThemePreference = useCallback((nextThemePreference: ThemePreference) => {
    setThemePreferenceState(nextThemePreference);
  }, []);

  return useMemo(
    () => ({
      setThemePreference,
      themePreference,
    }),
    [setThemePreference, themePreference],
  );
}
