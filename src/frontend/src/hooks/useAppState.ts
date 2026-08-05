import { useCallback, useEffect, useMemo, useState } from "react";

export type ThemePreference = "light" | "dark";
export type LocalePreference = "en" | "zh-CN";

const THEME_STORAGE_KEY = "medimage.themePreference";
const FALLBACK_THEME: ThemePreference = "light";
const LOCALE_STORAGE_KEY = "medimage.localePreference";
const FALLBACK_LOCALE: LocalePreference = "en";
const ADVANCED_MODE_STORAGE_KEY = "medimage.advancedMode";

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "light" || value === "dark";
}

function isLocalePreference(value: string | null): value is LocalePreference {
  return value === "en" || value === "zh-CN";
}

function readStoredLocalePreference(): LocalePreference {
  if (typeof window === "undefined") return FALLBACK_LOCALE;
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLocalePreference(stored) ? stored : FALLBACK_LOCALE;
  } catch {
    return FALLBACK_LOCALE;
  }
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

function readStoredAdvancedMode(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(ADVANCED_MODE_STORAGE_KEY) === "true";
  } catch {
    return false;
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
  const [localePreference, setLocalePreferenceState] = useState<LocalePreference>(
    readStoredLocalePreference,
  );
  const [advancedMode, setAdvancedModeState] = useState(readStoredAdvancedMode);

  useEffect(() => {
    applyThemePreference(themePreference);
    persistThemePreference(themePreference);
  }, [themePreference]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, localePreference);
    } catch {
      // Locale remains active for this session when storage is unavailable.
    }
    document.documentElement.lang = localePreference;
  }, [localePreference]);

  useEffect(() => {
    try {
      window.localStorage.setItem(ADVANCED_MODE_STORAGE_KEY, String(advancedMode));
    } catch {
      // The opt-in remains effective for this session when storage is unavailable.
    }
  }, [advancedMode]);

  const setThemePreference = useCallback((nextThemePreference: ThemePreference) => {
    setThemePreferenceState(nextThemePreference);
  }, []);

  const setLocalePreference = useCallback((nextLocalePreference: LocalePreference) => {
    setLocalePreferenceState(nextLocalePreference);
  }, []);

  const setAdvancedMode = useCallback((enabled: boolean) => {
    setAdvancedModeState(enabled);
  }, []);

  return useMemo(
    () => ({
      setThemePreference,
      themePreference,
      localePreference,
      setLocalePreference,
      advancedMode,
      setAdvancedMode,
    }),
    [
      advancedMode,
      localePreference,
      setAdvancedMode,
      setLocalePreference,
      setThemePreference,
      themePreference,
    ],
  );
}
