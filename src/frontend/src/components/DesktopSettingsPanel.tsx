import { useEffect, useState } from "react";
import { getDesktopConfig, getDesktopHealth, saveDesktopConfig } from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";

type Props = {
  baseUrl: string;
};

type Settings = {
  project_dir: string;
  python_path: string;
  matlab_command: string;
  spm_dir: string;
  dpabi_dir: string;
  gpu_mode: string;
  llm: {
    enabled: boolean;
    base_url: string;
    model: string;
    api_key?: string;
    api_key_set?: boolean;
  };
  gui_agent: {
    provider: string;
    approved: boolean;
  };
};

const EMPTY_SETTINGS: Settings = {
  project_dir: ".",
  python_path: "",
  matlab_command: "matlab",
  spm_dir: "./third_party/spm12",
  dpabi_dir: "./third_party/DPABI_V8.2_240510",
  gpu_mode: "prefer",
  llm: {
    enabled: false,
    base_url: "https://api.openai.com/v1",
    model: "",
    api_key: "",
    api_key_set: false,
  },
  gui_agent: {
    provider: "mock",
    approved: false,
  },
};

export default function DesktopSettingsPanel({ baseUrl }: Props) {
  const [settings, setSettings] = useState<Settings>(EMPTY_SETTINGS);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const desktopRuntime = window.MEDIMAGE_DESKTOP_RUNTIME || window.medimageDesktop?.runtime || null;

  useEffect(() => {
    void refresh();
  }, [baseUrl]);

  async function refresh() {
    setError("");
    try {
      const [configPayload, healthPayload] = await Promise.all([
        getDesktopConfig(baseUrl),
        getDesktopHealth(baseUrl),
      ]);
      setSettings({ ...EMPTY_SETTINGS, ...((configPayload.config as Partial<Settings>) || {}) });
      setHealth(healthPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      await saveDesktopConfig(baseUrl, settings as unknown as Record<string, unknown>);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  return (
    <div>
      {error ? <div className="errorBox">{error}</div> : null}
      <div className="formGrid">
        <label>
          Project directory
          <input
            value={settings.project_dir}
            onChange={(event) => update("project_dir", event.target.value)}
          />
        </label>
        <label>
          Python path
          <input
            value={settings.python_path}
            onChange={(event) => update("python_path", event.target.value)}
          />
        </label>
        <label>
          MATLAB command
          <input
            value={settings.matlab_command}
            onChange={(event) => update("matlab_command", event.target.value)}
          />
        </label>
        <label>
          SPM directory
          <input
            value={settings.spm_dir}
            onChange={(event) => update("spm_dir", event.target.value)}
          />
        </label>
        <label>
          DPABI directory
          <input
            value={settings.dpabi_dir}
            onChange={(event) => update("dpabi_dir", event.target.value)}
          />
        </label>
        <label>
          GPU mode
          <select
            value={settings.gpu_mode}
            onChange={(event) => update("gpu_mode", event.target.value)}
          >
            <option value="prefer">Prefer GPU</option>
            <option value="require">Require GPU</option>
            <option value="off">CPU only</option>
          </select>
        </label>
        <label>
          LLM base URL
          <input
            value={settings.llm.base_url}
            onChange={(event) => update("llm", { ...settings.llm, base_url: event.target.value })}
          />
        </label>
        <label>
          LLM model
          <input
            value={settings.llm.model}
            onChange={(event) => update("llm", { ...settings.llm, model: event.target.value })}
          />
        </label>
        <label>
          LLM API key
          <input
            type="password"
            placeholder={settings.llm.api_key_set ? "Configured" : "Not configured"}
            value={settings.llm.api_key || ""}
            onChange={(event) => update("llm", { ...settings.llm, api_key: event.target.value })}
          />
        </label>
        <label>
          GUI provider (mock only)
          <select
            value={settings.gui_agent.provider}
            onChange={(event) =>
              update("gui_agent", { ...settings.gui_agent, provider: event.target.value })
            }
          >
            <option value="mock">Mock (safe default)</option>
            <option value="pywinauto" disabled>
              pywinauto (blocked)
            </option>
          </select>
        </label>
      </div>
      <div className="row">
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={settings.llm.enabled}
            onChange={(event) => update("llm", { ...settings.llm, enabled: event.target.checked })}
          />
          Enable LLM planner
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={settings.gui_agent.approved}
            onChange={(event) =>
              update("gui_agent", { ...settings.gui_agent, approved: event.target.checked })
            }
          />
          Enable GUI Agent (mock-only, record_observation)
        </label>
        <button onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Save settings"}
        </button>
        <button onClick={refresh}>Refresh checks</button>
      </div>
      <h3>Desktop runtime</h3>
      <JsonBlock value={desktopRuntime} emptyText="Browser mode" />
      <h3>Health checks</h3>
      <JsonBlock value={health} emptyText="No desktop health checks yet" />
    </div>
  );
}
