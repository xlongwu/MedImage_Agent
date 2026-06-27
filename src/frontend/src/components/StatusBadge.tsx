import { Badge, type BadgeProps } from "./ui";

type Props = {
  status?: string | boolean | null;
};

export function StatusBadge({ status }: Props) {
  const text = typeof status === "boolean" ? (status ? "OK" : "FAILED") : status || "UNKNOWN";

  const normalized = String(text).toUpperCase();

  let tone: BadgeProps["tone"] = "neutral";
  if (["OK", "SUCCESS", "HEALTHY"].includes(normalized)) {
    tone = "success";
  } else if (["FAILED", "ERROR", "INVALID"].includes(normalized)) {
    tone = "danger";
  } else if (["PARTIAL", "WARNING", "MANUAL_REVIEW"].includes(normalized)) {
    tone = "warning";
  }

  return <Badge tone={tone}>{text}</Badge>;
}
