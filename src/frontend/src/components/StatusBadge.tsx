type Props = {
  status?: string | boolean | null;
};

export function StatusBadge({ status }: Props) {
  const text = typeof status === "boolean" ? (status ? "OK" : "FAILED") : status || "UNKNOWN";

  const normalized = String(text).toUpperCase();

  let className = "badge";
  if (["OK", "SUCCESS", "HEALTHY"].includes(normalized)) {
    className += " badgeSuccess";
  } else if (["FAILED", "ERROR", "INVALID"].includes(normalized)) {
    className += " badgeError";
  } else if (["PARTIAL", "WARNING", "MANUAL_REVIEW"].includes(normalized)) {
    className += " badgeWarning";
  }

  return <span className={className}>{text}</span>;
}
