import type { LocalePreference } from "../hooks/useAppState";

export function formatNumber(locale: LocalePreference, value: number): string {
  return new Intl.NumberFormat(locale).format(value);
}

export function formatDate(locale: LocalePreference, value: string | number | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatRelativeTime(
  locale: LocalePreference,
  value: number,
  unit: Intl.RelativeTimeFormatUnit,
): string {
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(value, unit);
}
