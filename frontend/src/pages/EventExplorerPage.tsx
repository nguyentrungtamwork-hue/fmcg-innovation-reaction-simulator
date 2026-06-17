import { Fragment, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { listEvents } from "../api/events";
import { getEventsSummary } from "../api/simulation";
import type { EventFilters, EventOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import AgentDrawer from "../components/AgentDrawer";
import { num, pct, titleCase } from "../utils/formatters";

export default function EventExplorerPage() {
  const { projectId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [events, setEvents] = useState<EventOut[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(searchParams.get("event_id"));
  const [drawerAgent, setDrawerAgent] = useState<string | null>(
    searchParams.get("open_agent") ? searchParams.get("agent_id") : null
  );

  const [actions, setActions] = useState<string[]>([]);
  const [segments, setSegments] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);

  const roundParam = searchParams.get("round_number");
  const [filters, setFilters] = useState<EventFilters>({
    limit: 1000,
    agent_id: searchParams.get("agent_id") ?? undefined,
    round_number: roundParam ? Number(roundParam) : undefined,
    action_type: searchParams.get("action_type") ?? undefined,
    segment_name: searchParams.get("segment_name") ?? undefined,
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setEvents(await listEvents(projectId, filters));
      setPage(0);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // populate filter option lists from the summary
    getEventsSummary(projectId)
      .then((s) => {
        setActions(Object.keys(s.action_distribution).sort());
        setSegments(Object.keys(s.segment_summary).sort());
      })
      .catch(() => {
        /* none yet */
      });
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function update<K extends keyof EventFilters>(key: K, value: EventFilters[K]) {
    setFilters((f) => ({ ...f, [key]: value === "" ? undefined : value }));
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Event explorer</h1>
          <p className="text-sm text-slate-500">Baseline simulation events. Filter, inspect reasoning, and open agents.</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to={`/projects/${projectId}/studio`}>Agent Studio</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/workflow`}>← Workflow</Link>
        </div>
      </div>

      <div className="card grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label className="label" htmlFor="f-round">Round</label>
          <select id="f-round" className="input" value={filters.round_number ?? ""} onChange={(e) => update("round_number", e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">All</option>
            {[1, 2, 3, 4, 5, 6].map((r) => (
              <option key={r} value={r}>Round {r}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-type">Agent type</label>
          <select id="f-type" className="input" value={filters.agent_type ?? ""} onChange={(e) => update("agent_type", e.target.value || undefined)}>
            <option value="">All</option>
            <option value="consumer">Consumer</option>
            <option value="market_actor">Market actor</option>
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-seg">Segment</label>
          <select id="f-seg" className="input" value={filters.segment_name ?? ""} onChange={(e) => update("segment_name", e.target.value || undefined)}>
            <option value="">All</option>
            {segments.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-action">Action</label>
          <select id="f-action" className="input" value={filters.action_type ?? ""} onChange={(e) => update("action_type", e.target.value || undefined)}>
            <option value="">All</option>
            {actions.map((a) => (
              <option key={a} value={a}>{titleCase(a)}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button className="btn-primary w-full" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Apply filters"}
          </button>
        </div>
      </div>

      {error ? <ErrorState error={error} onRetry={load} /> : null}
      {loading && <LoadingState label="Loading events…" />}

      {events && !loading && (
        <div className="card overflow-x-auto">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <span>
              {events.length === 0 ? "0 events" : `Showing ${page * pageSize + 1}·${Math.min((page + 1) * pageSize, events.length)} of ${events.length}`}
            </span>
            <div className="flex items-center gap-2">
              <label htmlFor="pg-size">Page size</label>
              <select id="pg-size" className="input py-1" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}>
                {[50, 100, 200].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <button className="btn-secondary py-1" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Prev</button>
              <button className="btn-secondary py-1" disabled={(page + 1) * pageSize >= events.length} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-2">Rnd</th>
                <th className="px-2">Agent / segment</th>
                <th className="px-2">Touchpoint</th>
                <th className="px-2">Action</th>
                <th className="px-2">Sent.</th>
                <th className="px-2">Trial</th>
                <th className="px-2">Intent</th>
                <th className="px-2">Repeat</th>
                <th className="px-2">Barrier / trigger</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(page * pageSize, (page + 1) * pageSize).map((ev) => (
                <Fragment key={ev.id}>
                  <tr
                    className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                    onClick={() => setExpanded((x) => (x === ev.id ? null : ev.id))}
                  >
                    <td className="py-2 pr-2 font-medium">{ev.round_number}</td>
                    <td className="px-2">
                      <button
                        className="text-brand-700 hover:underline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDrawerAgent(ev.agent_id);
                        }}
                      >
                        {ev.segment_name ?? titleCase(ev.agent_type)}
                      </button>
                    </td>
                    <td className="px-2 text-slate-600">{ev.touchpoint ?? "·"}</td>
                    <td className="px-2">{titleCase(ev.action_type)}</td>
                    <td className="px-2">{num(ev.sentiment_score, 2)}</td>
                    <td className="px-2">{pct(ev.trial_probability)}</td>
                    <td className="px-2">{pct(ev.purchase_intent_score)}</td>
                    <td className="px-2">{pct(ev.repeat_probability)}</td>
                    <td className="px-2 text-xs">
                      {ev.barrier_detected && <span className="text-red-600">{ev.barrier_detected}</span>}
                      {ev.barrier_detected && ev.trigger_detected && " · "}
                      {ev.trigger_detected && <span className="text-emerald-600">{ev.trigger_detected}</span>}
                      {!ev.barrier_detected && !ev.trigger_detected && "·"}
                    </td>
                  </tr>
                  {expanded === ev.id && (
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <td colSpan={9} className="px-2 py-3">
                        <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                          <Field label="Stage" value={ev.stage_name} />
                          <Field label="Emotional tone" value={ev.emotional_tone ?? "·"} />
                          <Field label="Confidence" value={num(ev.confidence_score, 2)} />
                          <Field label="Event ID" value={ev.id} mono />
                          <Field label="Reasoning" value={ev.reasoning ?? "·"} full />
                          <Field label="Generated reaction" value={ev.generated_reaction ?? "·"} full />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AgentDrawer projectId={projectId} agentId={drawerAgent} onClose={() => setDrawerAgent(null)} />
    </div>
  );
}

function Field({ label, value, full, mono }: { label: string; value: string; full?: boolean; mono?: boolean }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <span className="font-semibold text-slate-500">{label}: </span>
      <span className={mono ? "font-mono text-[10px]" : ""}>{value}</span>
    </div>
  );
}
