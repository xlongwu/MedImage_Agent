import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../I18nProvider";
import { messagesEn } from "../messages/en";
import { messagesZhCn } from "../messages/zh-CN";
import { useI18n } from "../useI18n";

describe("i18n", () => {
  it("keeps English and Simplified Chinese catalogs in parity", () => {
    expect(Object.keys(messagesZhCn).sort()).toEqual(Object.keys(messagesEn).sort());
  });

  it("renders English by default and interpolates Chinese messages", () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <I18nProvider locale="zh-CN">{children}</I18nProvider>
    );
    const { result } = renderHook(() => useI18n(), { wrapper });

    expect(result.current.t("projects.title")).toBe("最近项目");
    expect(result.current.t("projects.removeDescription", { name: "Study_01" })).toContain(
      "Study_01",
    );
  });
});
