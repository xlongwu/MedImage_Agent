import { useState } from "react";

import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import DesktopSettingsPanel from "../../components/DesktopSettingsPanel";
import EnvironmentHealthPanel from "../../components/EnvironmentHealthPanel";
import ExternalSmokePanel from "../../components/ExternalSmokePanel";
import ImportDiagnosticsPanel from "../../components/ImportDiagnosticsPanel";
import { RsfmriReleaseReadinessPanel } from "../../components/RsfmriReleaseReadinessPanel";
import SpmRealignDryRunPanel from "../../components/SpmRealignDryRunPanel";
import SpmRealignWrapperSkeletonPanel from "../../components/SpmRealignWrapperSkeletonPanel";
import RsfmriPresetPanel from "../../components/RsfmriPresetPanel";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import { Badge, Button, Card, SegmentedControl, Table } from "../../components/ui";
import type { ThemePreference } from "../../hooks/useAppState";
import type { PresetPlanDraft } from "../../types";
import styles from "./SettingsEnvironmentWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface SettingsEnvironmentWorkspaceProps {
  baseUrl: string;
  onThemePreferenceChange: (themePreference: ThemePreference) => void;
  projectId: string | null;
  rawdataDir?: string | null;
  themePreference: ThemePreference;
  onReviewDraft: (draft: PresetPlanDraft) => void;
}

export function SettingsEnvironmentWorkspace({
  baseUrl,
  onThemePreferenceChange,
  projectId,
  rawdataDir,
  themePreference,
  onReviewDraft,
}: SettingsEnvironmentWorkspaceProps) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Settings / Environment"
        subtitle="Environment, integrations, safety gates, diagnostics, and planning-only setup tools."
        status="Planning only"
      />
      <div className="planning-note">
        These tools produce readiness previews and review packages. They do not enable MATLAB/SPM
        execution or DPABI execution.
      </div>

      <nav className={styles.domainNav} aria-label="Settings domains">
        {SETTINGS_DOMAINS.map((item) => (
          <a href={`#settings-${item.slug}`} key={item.domain}>
            <span>{item.domain}</span>
            <small>{item.navLabel}</small>
          </a>
        ))}
      </nav>

      <section className={styles.settingsGrid} aria-label="Settings overview">
        <Card className={styles.mapCard} id="settings-general" tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h3>Settings map</h3>
              <p>
                Project-safe setup and diagnostics surfaces are grouped here for environment review.
              </p>
            </div>
            <Badge tone="info">Migrated</Badge>
          </div>
          <Table caption="Settings domains">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Scope</th>
                <th>Execution stance</th>
              </tr>
            </thead>
            <tbody>
              {SETTINGS_DOMAINS.map((item) => (
                <tr key={item.domain}>
                  <td>{item.domain}</td>
                  <td>{item.scope}</td>
                  <td>
                    <Badge tone={item.tone} size="sm">
                      {item.stance}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card className={styles.generalCard} id="settings-integrations">
          <div className={styles.cardHeader}>
            <div>
              <h3>General and integrations</h3>
              <p>
                User-facing preferences and provider connections are cataloged here without enabling
                hidden execution paths.
              </p>
            </div>
            <Badge tone="neutral">Config surface</Badge>
          </div>
          <div className={styles.preferenceStack} aria-label="General preferences">
            <div className={styles.preferenceRow}>
              <div>
                <span className={styles.preferenceLabel}>Theme</span>
                <p>
                  Applies the local workspace theme token set. Backend safety gates and execution
                  modes are unchanged.
                </p>
              </div>
              <SegmentedControl
                aria-label="Theme preference"
                options={THEME_OPTIONS}
                value={themePreference}
                onChange={(value) => onThemePreferenceChange(value as ThemePreference)}
              />
            </div>
          </div>
          <Table caption="General and integration controls">
            <thead>
              <tr>
                <th>Setting</th>
                <th>Current surface</th>
                <th>Authority</th>
              </tr>
            </thead>
            <tbody>
              {GENERAL_INTEGRATION_CONTROLS.map((item) => (
                <tr key={item.setting}>
                  <td>{item.setting}</td>
                  <td>{item.surface}</td>
                  <td>
                    <Badge tone={item.tone} size="sm">
                      {item.authority}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card className={styles.safetyCard} id="settings-safety">
          <div className={styles.cardHeader}>
            <div>
              <h3>Safety gates</h3>
              <p>Settings can prepare checks, but backend approval remains authoritative.</p>
            </div>
          </div>
          <dl className={styles.safetyList}>
            <div>
              <dt>External execution</dt>
              <dd>Disabled unless reviewed backend gates and environment flags allow it.</dd>
            </div>
            <div>
              <dt>Raw data</dt>
              <dd>Read-only policy remains outside UI toggle control.</dd>
            </div>
            <div>
              <dt>Diagnostics</dt>
              <dd>Loaded on demand to avoid accidental heavy checks during normal setup.</dd>
            </div>
          </dl>
          <Button variant="secondary" onClick={() => setShowDiagnostics((value) => !value)}>
            {showDiagnostics ? "Hide diagnostics modules" : "Open diagnostics modules"}
          </Button>
        </Card>

        <Card className={styles.policyCard} id="settings-diagnostics">
          <div className={styles.cardHeader}>
            <div>
              <h3>Safety policy matrix</h3>
              <p>
                Destructive or external behavior is represented as policy, not as a client-side
                shortcut.
              </p>
            </div>
            <Badge tone="warning">Backend owned</Badge>
          </div>
          <Table caption="Safety policy matrix">
            <thead>
              <tr>
                <th>Policy</th>
                <th>UI stance</th>
                <th>Gate</th>
              </tr>
            </thead>
            <tbody>
              {SAFETY_POLICY_ROWS.map((item) => (
                <tr key={item.policy}>
                  <td>{item.policy}</td>
                  <td>{item.stance}</td>
                  <td>
                    <Badge tone={item.tone} size="sm">
                      {item.gate}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      </section>

      <section
        className={styles.sectionStack}
        id="settings-environment"
        aria-label="Environment setup modules"
      >
        <div className={styles.sectionHeader}>
          <div>
            <h3>Environment setup</h3>
            <p>
              Lightweight readiness checks, SPM wrapper previews, and preset planning stay
              non-executing.
            </p>
          </div>
          <EvidenceBadge level="metadata_only">Readiness only</EvidenceBadge>
        </div>
        <div className={layoutStyles.panelGrid}>
          <div id="environment-health-panel">
            <EnvironmentHealthPanel baseUrl={baseUrl} />
          </div>
          <div id="spm-realign-dry-run-panel">
            <SpmRealignDryRunPanel baseUrl={baseUrl} projectId={projectId} />
          </div>
          <div id="spm-realign-wrapper-skeleton-panel">
            <SpmRealignWrapperSkeletonPanel baseUrl={baseUrl} projectId={projectId} />
          </div>
          <div id="rsfmri-preset-panel">
            <RsfmriPresetPanel
              baseUrl={baseUrl}
              projectId={projectId}
              onReviewDraft={onReviewDraft}
            />
          </div>
        </div>
      </section>

      {showDiagnostics ? (
        <section className={styles.sectionStack} aria-label="System diagnostics modules">
          <div className={styles.sectionHeader}>
            <div>
              <h3>System diagnostics</h3>
              <p>
                Desktop settings, import diagnostics, external smoke readiness, and release checks
                stay grouped here.
              </p>
            </div>
            <EvidenceBadge level="backend_required">On demand</EvidenceBadge>
          </div>
          <div className={layoutStyles.panelGrid}>
            <div id="desktop-settings-panel">
              <DesktopSettingsPanel baseUrl={baseUrl} />
            </div>
            <div id="import-diagnostics-panel">
              <ImportDiagnosticsPanel
                baseUrl={baseUrl}
                projectId={projectId}
                rawdataDir={rawdataDir}
              />
            </div>
            <div id="external-smoke-panel">
              <ExternalSmokePanel baseUrl={baseUrl} />
            </div>
            <div id="release-readiness-panel">
              <RsfmriReleaseReadinessPanel baseUrl={baseUrl} />
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const SETTINGS_DOMAINS: Array<{
  domain: string;
  navLabel: string;
  slug: string;
  scope: string;
  stance: string;
  tone: BadgeTone;
}> = [
  {
    domain: "General",
    navLabel: "Preferences",
    slug: "general",
    scope: "Desktop runtime, project directory, startup defaults",
    stance: "Config only",
    tone: "neutral",
  },
  {
    domain: "Environment",
    navLabel: "Readiness",
    slug: "environment",
    scope: "Python, MATLAB, SPM, DPABI, GPU readiness",
    stance: "Readiness",
    tone: "info",
  },
  {
    domain: "Integrations",
    navLabel: "Advisory",
    slug: "integrations",
    scope: "LLM planner and model provider settings",
    stance: "Disabled by default",
    tone: "warning",
  },
  {
    domain: "Safety",
    navLabel: "Backend gates",
    slug: "safety",
    scope: "Approval, rawdata policy, external smoke gates",
    stance: "Backend gated",
    tone: "warning",
  },
  {
    domain: "Diagnostics",
    navLabel: "On demand",
    slug: "diagnostics",
    scope: "Import handoff, desktop sidecar, release readiness",
    stance: "On demand",
    tone: "info",
  },
];

const THEME_OPTIONS = [
  { label: "Light", value: "light" },
  { label: "Dark", value: "dark" },
];

const GENERAL_INTEGRATION_CONTROLS: Array<{
  authority: string;
  setting: string;
  surface: string;
  tone: BadgeTone;
}> = [
  {
    setting: "Language / theme",
    surface: "Desktop settings module",
    authority: "Config only",
    tone: "neutral",
  },
  {
    setting: "Startup behavior",
    surface: "Desktop sidecar configuration",
    authority: "Config only",
    tone: "neutral",
  },
  {
    setting: "LLM provider",
    surface: "Model status and planner settings",
    authority: "Advisory only",
    tone: "info",
  },
  {
    setting: "External tools",
    surface: "Smoke readiness and release checks",
    authority: "Disabled by default",
    tone: "warning",
  },
];

const SAFETY_POLICY_ROWS: Array<{
  gate: string;
  policy: string;
  stance: string;
  tone: BadgeTone;
}> = [
  {
    policy: "Rawdata read-only",
    stance: "Expose policy status; do not offer write toggles",
    gate: "Invariant",
    tone: "danger",
  },
  {
    policy: "Overwrite strategy",
    stance: "Require reviewed backend plan before replacing outputs",
    gate: "Approval",
    tone: "warning",
  },
  {
    policy: "Approver requirement",
    stance: "Show required approval context without bypass actions",
    gate: "Backend gated",
    tone: "warning",
  },
  {
    policy: "External execution",
    stance: "Keep MATLAB, SPM, DPABI, GPU execution disabled until gated",
    gate: "Environment flag",
    tone: "info",
  },
];
