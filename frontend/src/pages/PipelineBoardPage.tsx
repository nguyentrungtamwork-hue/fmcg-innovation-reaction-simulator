import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  applyDecisionBoardToPipeline,
  getPipelineBoard,
  STAGE_LABELS,
  type PipelineBoard,
  type PipelineBoardFilters,
  type PipelineCardItem,
} from "../api/pipeline";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import UpdateStageModal from "../components/pipeline/UpdateStageModal";
import PipelineFilterBar from "../components/pipeline/PipelineFilterBar";

const RECENT_DAYS = 7;
function isRecent(ts: string | null | undefined): boolean {
  if (!ts) return false;
  const dt = Date.parse(ts);
  if (isNaN(dt)) return false;
  return Date.now() - dt < RECENT_DAYS * 24 * 3600 * 1000;
}

function paramsToFilters(sp: URLSearchParams): PipelineBoardFilters {
  const f: PipelineBoardFilters = {};
  const s = sp.get("stage"); if (s) f.stage = s;
  const dl = sp.get("decision_label"); if (dl) f.decision_label = dl;
  const ms = sp.get("min_score"); if (ms) f.min_score = Number(ms);
  const mr = sp.get("max_risk"); if (mr) f.max_risk = Number(mr);
  const ot = sp.get("owner_team"); if (ot) f.owner_team = ot;
  const q = sp.get("search"); if (q) f.search = q;
  if (sp.get("include_archived") === "false") f.include_archived = false;
  return f;
}

function filtersToParams(f: PipelineBoardFilters): URLSearchParams {
  const sp = new URLSearchParams();
  if (f.stage) sp.set("stage", f.stage);
  if (f.decision_label) sp.set("decision_label", f.decision_label);
  if (f.min_score != null) sp.set("min_score", String(f.min_score));
  if (f.max_risk != null) sp.set("max_risk", String(f.max_risk));
  if (f.owner_team) sp.set("owner_team", f.owner_team);
  if (f.search) sp.set("search", f.search);
  if (f.include_archived === false) sp.set("include_archived", "false");
  return sp;
}

const STAGE_TONE: Record<string, string> = {
  new_concept: "border-slate-200 bg-slate-50 text-slate-600",
  brief_submitted: "border-slate-200 bg-slate-50 text-slate-600",
  ready_for_simulation: "border-sky-200 bg-sky-50 text-sky-700",
  simulated: "border-sky-200 bg-sky-50 text-sky-700",
  report_ready: "border-indigo-200 bg-indigo-50 text-indigo-700",
  briefing_ready: "border-indigo-200 bg-indigo-50 text-indigo-700",
  leadership_review: "border-amber-200 bg-amber-50 text-amber-700",
  validate: "border-amber-200 bg-amber-50 text-amber-700",
  revise: "border-orange-200 bg-orange-50 text-orange-700",
  go: "border-emerald-200 bg-emerald-50 text-emerald-700",
  hold: "border-rose-200 bg-rose-50 text-rose-700",
  archived: "border-slate-200 bg-slate-50 text-slate-400",
};

function Card({ item, onUpdate }: { item: PipelineCardItem; onUpdate: (pid: string) => void }) {
  const recent = isRecent(item.pipeline_stage_updated_at);
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-2 text-sm shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <Link to={`/projects/${item.project_id}/home`} className="font-medium text-slate-900 hover:underline">
          {item.project_name}
        </Link>
        <div className="flex flex-col items-end gap-1">
          {recent && (
            <span
              className="chip border-amber-200 bg-amber-50 text-amber-700"
              title={`Stage changed within the last ${RECENT_DAYS} days`}
            >
              Recently changed
            </span>
          )}
          {item.decision_board_label && (
            <span className={`chip ${STAGE_TONE[item.decision_board_label] ?? "border-slate-200 bg-slate-50 text-slate-500"}`}>
              {item.decision_board_label}
            </span>
          )}
        </div>
      </div>
      <div className="mt-1 text-xs text-slate-500">
        {item.overall_score != null && <span>Score {Math.round(item.overall_score)}/100</span>}
        {item.top_risk && <span className="ml-2">Risk: {item.top_risk}</span>}
      </div>
      <p className="mt-1 text-xs text-slate-600">{item.next_recommended_action.label}</p>
      <div className="mt-2 flex flex-wrap gap-1 text-xs">
        <Link className="text-brand-700 hover:underline" to={`/projects/${item.project_id}/home`}>Home</Link>
        <span className="text-slate-300">·</span>
        <Link className="text-brand-700 hover:underline" to={`/projects/${item.project_id}/studio`}>Studio</Link>
        {item.has_decision_pack && (
          <>
            <span className="text-slate-300">·</span>
            <Link className="text-brand-700 hover:underline" to={`/projects/${item.project_id}/decision-pack`}>Decision Pack</Link>
            <span className="text-slate-300">·</span>
            <Link className="text-brand-700 hover:underline" to={`/projects/${item.project_id}/briefing`}>Briefing</Link>
          </>
        )}
        <span className="text-slate-300">·</span>
        <button className="text-brand-700 hover:underline" onClick={() => onUpdate(item.project_id)}>Update Stage</button>
      </div>
    </article>
  );
}

export default function PipelineBoardPage() {
  const [board, setBoard] = useState<PipelineBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);
  const [updateOpen, setUpdateOpen] = useState<string | null>(null);

  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => paramsToFilters(searchParams), [searchParams]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setBoard(await getPipelineBoard(filters));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { void refresh(); }, [refresh]);

  const onFiltersChange = (f: PipelineBoardFilters) => setSearchParams(filtersToParams(f), { replace: true });
  const onClearFilters = () => setSearchParams(new URLSearchParams(), { replace: true });

  async function apply() {
    setApplying(true);
    setApplyResult(null);
    try {
      const r = await applyDecisionBoardToPipeline({ only_if_not_manual: true });
      setApplyResult(`Updated ${r.changed} · skipped (manual) ${r.skipped_manual} · skipped (no board) ${r.skipped_no_board}.`);
      await refresh();
    } catch (e: any) {
      setApplyResult(e?.message ?? "Apply failed.");
    } finally {
      setApplying(false);
    }
  }

  if (loading) return <LoadingState label="Building pipeline board…" />;
  if (error) return <ErrorState error={error} />;
  if (!board) return null;

  const s = board.summary;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Innovation Pipeline Board</h1>
            <p className="text-xs text-slate-400">Generated {String(board.generated_at).slice(0, 10)} · {s.total_projects} project(s)</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={applying} onClick={apply}>{applying ? "Applying…" : "Apply Decision Board"}</button>
            <Link className="btn-secondary" to="/portfolio/activity">Activity →</Link>
            <Link className="btn-secondary" to="/portfolio/decision-board">Open Decision Board</Link>
            <Link className="btn-secondary" to="/portfolio">← Portfolio</Link>
          </div>
        </div>
        {applyResult && <p className="mt-2 text-xs text-slate-600">{applyResult}</p>}
        <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <MetricCard label="Total" value={String(s.total_projects)} />
          <MetricCard label="New / Brief" value={String((s.new_count ?? 0) + (s.brief_submitted_count ?? 0))} />
          <MetricCard label="Report Ready" value={String(s.report_ready_count ?? 0)} />
          <MetricCard label="Briefing Ready" value={String(s.briefing_ready_count ?? 0)} />
          <MetricCard label="Validate" value={String(s.validate_count ?? 0)} />
          <MetricCard label="Go" value={String(s.go_count ?? 0)} />
        </div>
      </div>

      <PipelineFilterBar
        filters={filters}
        matched={s.total_projects ?? 0}
        total={(s as any).total_projects_unfiltered ?? s.total_projects ?? 0}
        onChange={onFiltersChange}
        onClear={onClearFilters}
      />

      <div className="overflow-x-auto">
        <div className="flex min-w-max gap-3">
          {board.columns.map((col) => (
            <section key={col.stage} className="w-72 shrink-0" aria-label={col.label}>
              <div className="mb-2 flex items-center justify-between">
                <span className={`chip ${STAGE_TONE[col.stage] ?? "border-slate-200 bg-slate-50 text-slate-500"}`}>{col.label}</span>
                <span className="text-xs text-slate-400">{col.items.length}</span>
              </div>
              <div className="space-y-2">
                {col.items.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-slate-200 p-3 text-xs text-slate-400">No projects.</p>
                ) : (
                  col.items.map((it) => <Card key={it.project_id} item={it} onUpdate={(pid) => setUpdateOpen(pid)} />)
                )}
              </div>
            </section>
          ))}
        </div>
      </div>

      <p className="text-center text-[11px] text-slate-400">
        Stages are a local tracking view — simulated outputs are exploratory decision support, not validated market forecasts.
      </p>

      {updateOpen && (
        <UpdateStageModal
          open
          projectId={updateOpen}
          current={null}
          onClose={() => setUpdateOpen(null)}
          onSaved={() => { setUpdateOpen(null); void refresh(); }}
        />
      )}
    </div>
  );
}
