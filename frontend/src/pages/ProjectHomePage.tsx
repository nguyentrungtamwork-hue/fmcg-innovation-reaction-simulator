import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getOverview } from "../api/overview";
import type { OverviewOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import StatusBadge from "../components/StatusBadge";
import MetricCard from "../components/MetricCard";
import { pct, shortDate, titleCase } from "../utils/formatters";
import { exportProjectBundle } from "../api/projects";
import HelpTooltip from "../components/HelpTooltip";
import { getActivity, getPipelineStatus, STAGE_LABELS, type ActivityItem, type PipelineStatus } from "../api/pipeline";
import UpdateStageModal from "../components/pipeline/UpdateStageModal";

const SURFACE_ROUTE: Record<string, string> = {
  workflow: "workflow", studio: "studio", report: "report", briefing: "briefing",
  scenarios: "scenarios", sensitivity: "sensitivity", events: "events", decisions: "decisions",
};

const QUICK_LINKS: [string, string][] = [
  ["Workflow", "workflow"], ["Agent Studio", "studio"], ["Events", "events"], ["Report", "report"],
  ["Briefing", "briefing"], ["Scenario Lab", "scenarios"], ["Sensitivity", "sensitivity"], ["Decisions", "decisions"],
];

export default function ProjectHomePage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<OverviewOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [pipelineOpen, setPipelineOpen] = useState(false);
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([]);

  function loadRecent(pid: string) {
    getActivity({ project_id: pid, limit: 3 })
      .then((r) => setRecentActivity(r.items))
      .catch(() => setRecentActivity([]));
  }

  function load() {
    setLoading(true);
    setError(null);
    getOverview(projectId).then(setData).catch(setError).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    getPipelineStatus(projectId).then(setPipeline).catch(() => setPipeline(null));
    loadRecent(projectId);
  }, [projectId]);

  if (loading) return <LoadingState label="Loading project overview…" />;
  if (error) return <ErrorState error={error} onRetry={load} />;
  if (!data) return null;

  const ps = data.pipeline_status;
  const na = data.next_recommended_action;
  const sc = data.latest_scorecard;
  const bs = data.latest_briefing_summary;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{data.project.name}</h1>
          <p className="text-sm text-slate-500">Project home — status, next step, and quick links. {[data.project.category, data.project.market].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-secondary"
            onClick={() => {
              exportProjectBundle(projectId)
                .then((bundle) => {
                  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `${data.project.name.replace(/\s+/g, "_")}_export.json`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  URL.revokeObjectURL(url);
                })
                .catch(() => undefined);
            }}
          >
            Export Project
          </button>
          <Link className="btn-secondary" to="/data-tools">Data Tools</Link>
        </div>
      </div>

      {/* What to do next */}
      <div className="card border-brand-200 bg-brand-50">
        <div className="label">What to do next</div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">{na.label}</div>
            <div className="text-sm text-slate-600">{na.reason}</div>
          </div>
          <button className="btn-primary" onClick={() => navigate(`/projects/${projectId}/${SURFACE_ROUTE[na.surface] ?? "workflow"}`)}>
            Go →
          </button>
        </div>
      </div>

      {/* Pipeline status */}
      <div className="card">
        <div className="label">Pipeline status<HelpTooltip term="ontology" label="ontology" /></div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge ready={ps.has_brief} label="Brief" />
          <StatusBadge ready={ps.has_ontology} label="Ontology" />
          <StatusBadge ready={ps.has_agents} label="Agents" />
          <StatusBadge ready={ps.has_simulation} label="Simulation" />
          <StatusBadge ready={ps.has_report} label="Report" />
          <StatusBadge ready={ps.has_briefing} label="Briefing" />
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-5">
          <MetricCard label="Agents" value={String(data.counts.agents)} />
          <MetricCard label="Events" value={String(data.counts.events)} />
          <MetricCard label="Snapshots" value={String(data.counts.snapshots)} />
          <MetricCard label="Scenarios" value={String(data.counts.scenarios)} />
          <MetricCard label="Decisions" value={String(data.counts.decisions)} />
        </div>
        {data.latest_live_run && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>Latest live run:</span>
            <span className={`chip ${data.latest_live_run.is_stale ? "border-amber-200 bg-amber-50 text-amber-700" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
              {data.latest_live_run.status}{data.latest_live_run.is_stale ? " · stale" : ""}
            </span>
            <span>{data.latest_live_run.total_events_emitted} events</span>
            {data.latest_live_run.is_stale && <Link className="text-brand-700 underline" to={`/projects/${projectId}/studio`}>Resolve in Studio →</Link>}
          </div>
        )}
      </div>

      {/* Latest recommendation */}
      <div className="card">
        <div className="mb-2 flex items-center justify-between">
          <div className="label mb-0">Latest recommendation</div>
          <Link className="btn-secondary" to={`/projects/${projectId}/briefing`}>{bs ? "Open Briefing" : "Generate Briefing"}</Link>
        </div>
        {sc || bs ? (
          <div className="grid gap-3 md:grid-cols-4">
            {sc && <MetricCard label="Overall score" value={`${sc.overall_score}/100`} tone="up" />}
            {bs && <InfoCard label="Recommendation" value={titleCase(bs.recommendation_status)} />}
            {sc && <InfoCard label="Confidence" value={`${sc.confidence_label} (${pct(sc.confidence_score)})`} />}
            {sc && <InfoCard label="Top opportunity" value={sc.top_opportunity} />}
            {sc && <InfoCard label="Top risk" value={sc.top_risk} />}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No scorecard yet — generate the report to see the recommendation.</p>
        )}
      </div>

      {/* Quick links */}
      <div className="card">
        <div className="label">Quick links</div>
        <div className="flex flex-wrap gap-2">
          {QUICK_LINKS.map(([label, surface]) => (
            <Link key={surface} className="btn-secondary" to={`/projects/${projectId}/${surface}`}>{label}</Link>
          ))}
          <Link className="btn-secondary" to="/portfolio">Portfolio</Link>
          <Link className="btn-secondary" to="/portfolio/decision-board">Decision Board</Link>
          <Link className="btn-secondary" to="/compare">Compare</Link>
          <Link className="btn-secondary" to="/samples">Samples</Link>
          <Link className="btn-primary" to={`/projects/${projectId}/decision-pack`}>Open Decision Pack</Link>
        </div>
      </div>

      {pipeline && (
        <div className="card flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-500">Pipeline stage:</span>
          <span className="chip border-brand-200 bg-brand-50 text-brand-700">
            {pipeline.pipeline_stage_label}
            <span className="ml-1 text-[10px] text-brand-500">({pipeline.pipeline_stage_source})</span>
          </span>
          {pipeline.inferred_stage !== pipeline.pipeline_stage && (
            <span className="text-xs text-slate-400">Inferred: {STAGE_LABELS[pipeline.inferred_stage] ?? pipeline.inferred_stage}</span>
          )}
          {pipeline.next_recommended_action?.label && (
            <span className="text-xs text-slate-500">Next: {pipeline.next_recommended_action.label}</span>
          )}
          <span className="ml-auto flex gap-2">
            <button className="btn-secondary" onClick={() => setPipelineOpen(true)}>Update Stage</button>
            <Link className="btn-secondary" to="/portfolio/pipeline">Open Pipeline Board</Link>
          </span>
        </div>
      )}

      {pipeline && (
        <div className="card">
          <div className="mb-2 flex items-center justify-between">
            <div className="label mb-0">Recent pipeline activity</div>
            <div className="flex gap-2 text-xs">
              <Link className="text-brand-700 underline" to={`/projects/${projectId}/decisions`}>Decision history</Link>
              <Link className="text-brand-700 underline" to="/portfolio/pipeline">Pipeline board</Link>
            </div>
          </div>
          {recentActivity.length === 0 ? (
            <p className="text-sm text-slate-500">No pipeline changes yet.</p>
          ) : (
            <ul className="space-y-2">
              {recentActivity.map((it) => (
                <li key={it.id} className="border-b border-slate-100 pb-1 text-sm last:border-b-0">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-slate-800">{it.title}</span>
                    <span className="text-xs text-slate-400">{it.timestamp ? new Date(it.timestamp).toLocaleString() : "—"}</span>
                  </div>
                  {it.description && <p className="text-xs text-slate-500">{it.description}</p>}
                  {it.stage && <span className="chip border-brand-200 bg-brand-50 text-brand-700">{STAGE_LABELS[it.stage] ?? it.stage}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <UpdateStageModal
        open={pipelineOpen}
        projectId={projectId}
        current={pipeline}
        onClose={() => setPipelineOpen(false)}
        onSaved={(s) => { setPipeline(s); setPipelineOpen(false); loadRecent(projectId); }}
      />

      {!ps.has_brief && (
        <div className="card border-amber-200 bg-amber-50 text-sm text-amber-800">
          This project has no brief yet. Paste one in the <Link className="underline" to={`/projects/${projectId}/workflow`}>Workflow</Link>,
          {" "}<Link className="underline" to="/samples">load a sample concept</Link>, or{" "}
          <Link className="underline" to="/data-tools">import a project bundle</Link>.
        </div>
      )}

      {/* Recent activity */}
      <div className="card">
        <div className="label">Recent activity</div>
        {data.recent_activity.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {data.recent_activity.map((a, i) => (
              <li key={i} className="flex items-center justify-between border-b border-slate-100 py-1">
                <span className="text-slate-700">{a.title}</span>
                <span className="text-xs text-slate-400">{shortDate(a.timestamp)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="label">{label}</div>
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}
