import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getActivity, PIPELINE_STAGES, STAGE_LABELS, type ActivityItem } from "../api/pipeline";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

const ACTIVITY_TYPES = ["stage_change", "decision", "snapshot", "scenario", "report", "briefing"];

function shortDate(ts: string | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts.slice(0, 10);
  }
}

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <li className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="chip border-slate-200 bg-slate-50 text-slate-600">{item.activity_type}</span>
          {item.stage && (
            <span className="chip border-brand-200 bg-brand-50 text-brand-700">
              {STAGE_LABELS[item.stage] ?? item.stage}
            </span>
          )}
          <Link to={`/projects/${item.project_id}/home`} className="font-medium text-slate-800 hover:underline">
            {item.project_name || item.project_id.slice(0, 8)}
          </Link>
        </div>
        <span className="text-xs text-slate-400">{shortDate(item.timestamp)}</span>
      </div>
      <div className="text-slate-700">{item.title}</div>
      {item.description && <p className="text-xs text-slate-500">{item.description}</p>}
      <div>
        <Link to={item.related_url} className="text-xs font-medium text-brand-700 hover:underline">
          Open →
        </Link>
      </div>
    </li>
  );
}

export default function PortfolioActivityPage() {
  const [items, setItems] = useState<ActivityItem[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [eventType, setEventType] = useState<string>("");
  const [stage, setStage] = useState<string>("");
  const [limit, setLimit] = useState<number>(50);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const r = await getActivity({
        event_type: eventType || undefined,
        stage: stage || undefined,
        limit,
      });
      setItems(r.items);
    } catch (e) {
      setError(e);
    } finally {
      setRefreshing(false);
    }
  }, [eventType, stage, limit]);

  useEffect(() => { void refresh(); }, [refresh]);

  const grouped = useMemo(() => {
    if (!items) return [];
    const by: Record<string, ActivityItem[]> = {};
    for (const it of items) {
      const day = (it.timestamp ?? "—").slice(0, 10);
      (by[day] ||= []).push(it);
    }
    return Object.entries(by).sort(([a], [b]) => (a < b ? 1 : -1));
  }, [items]);

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Portfolio Activity</h1>
          <p className="text-xs text-slate-400">Recent cross-project changes from the decision log.</p>
        </div>
        <div className="ml-auto flex flex-wrap items-end gap-2">
          <div>
            <label htmlFor="activity-type" className="label">Type</label>
            <select id="activity-type" className="input py-1 text-sm" value={eventType} onChange={(e) => setEventType(e.target.value)}>
              <option value="">All</option>
              {ACTIVITY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="activity-stage" className="label">Stage</label>
            <select id="activity-stage" className="input py-1 text-sm" value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">Any</option>
              {PIPELINE_STAGES.map((s) => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="activity-limit" className="label">Limit</label>
            <input
              id="activity-limit"
              type="number"
              min={1}
              max={100}
              className="input w-20 py-1 text-sm"
              value={limit}
              onChange={(e) => setLimit(Math.max(1, Math.min(100, Number(e.target.value) || 50)))}
            />
          </div>
          <button className="btn-secondary" disabled={refreshing} onClick={refresh}>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <Link className="btn-secondary" to="/portfolio/pipeline">← Pipeline</Link>
        </div>
      </div>

      {error != null && <ErrorState error={error} />}
      {items === null ? (
        <LoadingState label="Loading activity…" />
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">No recent activity. Move a project's stage or generate a report.</p>
      ) : (
        <div className="space-y-4">
          {grouped.map(([day, rows]) => (
            <section key={day}>
              <div className="label mb-1">{day}</div>
              <ul className="space-y-2">
                {rows.map((it) => <ActivityRow key={it.id} item={it} />)}
              </ul>
            </section>
          ))}
        </div>
      )}
      <p className="text-center text-[11px] text-slate-400">
        Activity is local and read-only. No real-time notifications.
      </p>
    </div>
  );
}
