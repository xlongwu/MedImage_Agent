import { useMemo, type ReactNode } from "react";

import type { LocalePreference } from "../hooks/useAppState";
import { messagesEn } from "./messages/en";
import { messagesZhCn } from "./messages/zh-CN";
import { I18nContext, type I18nContextValue } from "./context";

export function I18nProvider({
  children,
  locale,
}: {
  children: ReactNode;
  locale: LocalePreference;
}) {
  const value = useMemo<I18nContextValue>(() => {
    const catalog = locale === "zh-CN" ? messagesZhCn : messagesEn;
    return {
      locale,
      t: (key, values) => {
        const template = catalog[key] ?? messagesEn[key] ?? key;
        if (!values) return template;
        return Object.entries(values).reduce(
          (message, [name, replacement]) => message.split(`{${name}}`).join(String(replacement)),
          template,
        );
      },
    };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
