import { createContext } from "react";

import type { LocalePreference } from "../hooks/useAppState";
import type { MessageKey } from "./messages/en";
import { messagesEn } from "./messages/en";

export type InterpolationValues = Record<string, string | number>;

export type I18nContextValue = {
  locale: LocalePreference;
  t: (key: MessageKey, values?: InterpolationValues) => string;
};

export const I18nContext = createContext<I18nContextValue>({
  locale: "en",
  t: (key, values) => {
    let message: string = messagesEn[key] ?? key;
    if (!values) return message;
    for (const [name, replacement] of Object.entries(values)) {
      message = message.split(`{${name}}`).join(String(replacement));
    }
    return message;
  },
});
