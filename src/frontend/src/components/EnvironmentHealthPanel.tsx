import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getDesktopHealth } from "../lib/api";
import { useI18n } from "../i18n/useI18n";

type Props = { baseUrl?: string };

const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};

export default function EnvironmentHealthPanel({ baseUrl }: Props) {
  const { t } = useI18n();
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const reqRef = useRef(0);

  useEffect(() => {
    const id = reqRef.current + 1;
    reqRef.current = id;
    /* eslint-disable react-hooks/set-state-in-effect -- A base URL change starts a new guarded health request. */
    setLoading(true);
    setError("");
    /* eslint-enable react-hooks/set-state-in-effect */
    getDesktopHealth(effectiveBase)
      .then((d) => {
        if (id === reqRef.current) setData(d);
      })
      .catch((e) => {
        if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (id === reqRef.current) setLoading(false);
      });
  }, [effectiveBase]);

  if (loading)
    return (
      <Sec>
        <H3>{t("settings.health.title")}</H3>
        <div className="empty">{t("settings.health.checking")}</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>{t("settings.health.title")}</H3>
        <div className="errorBox">{error}</div>
      </Sec>
    );
  if (!data) return null;

  const ms = (data.matlab_spm ?? {}) as Record<string, unknown>;
  const matlab = (ms.matlab ?? {}) as Record<string, unknown>;
  const spm = (ms.spm ?? {}) as Record<string, unknown>;

  return (
    <Sec>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          marginBottom: 12,
        }}
      >
        <div>
          <H3>{t("settings.health.title")}</H3>
          <Sub>{t("settings.health.description")}</Sub>
        </div>
        <span
          style={{
            ...pill,
            background:
              ms.status === "ready_for_dry_run_check"
                ? "#e8f5e9"
                : ms.status === "warning"
                  ? "#fff7ed"
                  : "#ffebee",
            color:
              ms.status === "ready_for_dry_run_check"
                ? "#176b3b"
                : ms.status === "warning"
                  ? "#9a5a15"
                  : "#b53b3b",
            borderColor: "rgba(137, 150, 171, 0.28)",
          }}
        >
          {((ms.status as string) ?? "unknown").toUpperCase()}
        </span>
      </div>
      <div
        style={{
          padding: 8,
          border: "1px solid rgba(242, 153, 74, 0.28)",
          borderRadius: 6,
          background: "rgba(255, 251, 242, 0.94)",
          fontSize: 11,
          color: "#9a5a15",
          marginBottom: 12,
        }}
      >
        {t("settings.health.boundary")}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div style={card}>
          <strong style={{ fontSize: 13 }}>MATLAB</strong>
          <BoolRow label={t("settings.health.configured")} v={matlab.configured as boolean} />
          <BoolRow label={t("settings.health.exists")} v={matlab.exists as boolean} />
          <ValRow label={t("settings.health.path")} v={matlab.executable_path as string} />
          <ValRow label={t("settings.health.version")} v={matlab.version as string} />
          <BoolRow label={t("settings.health.versionOk")} v={matlab.version_check_ok as boolean} />
        </div>
        <div style={card}>
          <strong style={{ fontSize: 13 }}>SPM</strong>
          <BoolRow label={t("settings.health.configured")} v={spm.configured as boolean} />
          <BoolRow label={t("settings.health.exists")} v={spm.exists as boolean} />
          <ValRow label={t("settings.health.path")} v={spm.spm_path as string} />
          <ValRow label={t("settings.health.version")} v={spm.version as string} />
          <BoolRow label={t("settings.health.versionOk")} v={spm.version_check_ok as boolean} />
        </div>
      </div>

      <div style={{ display: "grid", gap: 6, marginBottom: 12 }}>
        <BoolRow
          label={t("settings.health.realExecution")}
          v={ms.real_execution_enabled as boolean}
        />
        <BoolRow label={t("settings.health.allowlist")} v={ms.safe_allowlist_enabled as boolean} />
      </div>

      {(ms.notes as string[] | undefined)?.length ? (
        <div style={{ marginTop: 8 }}>
          {((ms.notes ?? []) as string[]).map((n, i) => (
            <div key={i} style={{ fontSize: 11, color: "#667085", marginBottom: 2 }}>
              • {n}
            </div>
          ))}
        </div>
      ) : null}
    </Sec>
  );
}

function BoolRow({ label, v }: { label: string; v: boolean | undefined }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
      <span>{label}</span>
      <b style={{ color: v ? "#176b3b" : "#b53b3b" }}>{v ? "✓" : "✗"}</b>
    </div>
  );
}
function ValRow({ label, v }: { label: string; v: string | undefined | null }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        fontSize: 11,
        overflowWrap: "anywhere",
      }}
    >
      <span>{label}</span>
      <b>{v || "—"}</b>
    </div>
  );
}

const card: React.CSSProperties = {
  padding: 12,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  display: "grid",
  gap: 6,
};
const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section
    style={{
      padding: 16,
      border: "1px solid rgba(137, 150, 171, 0.28)",
      borderRadius: 8,
      background: "rgba(255, 255, 255, 0.88)",
      marginTop: 4,
    }}
  >
    {children}
  </section>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>
);
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>
);
