import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { LiveRun, StudioGraph } from "../../types/api";
import { cancelLiveRun, listLiveRuns } from "../../api/liveSimulation";
import { useLiveSimulation } from "../../hooks/useLiveSimulation";
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion";
import { shortDate } from "../../utils/formatters";
import AgentNetworkCanvas from "./AgentNetworkCanvas";
import LiveSimulationControls from "./LiveSimulationControls";
import LiveProgressBar from "./LiveProgressBar";
import LiveStatusBadge from "./LiveStatusBadge";
import MetricCard from "../MetricCard";
import { num, titleCase, stanceMeta } from "../../utils/formatters";

interface Props {
  projectId: string;
  graph: StudioGraph;
  onCompleted: () => void;
  onInspect: (agentId: string) => void;
}

export default function LivePanel({ projectId, graph, onCompleted, onInspect }: Props) {
  const live = useLiveSimulation(projectId);
  const reducedMotion = usePrefersReducedMotion();
  const streaming = live.status === "starting" || live.status === "streaming";
  const m = live.metrics;
  const [streamCap, setStreamCap] = useState(40);

  const [runs, setRuns] = useState<LiveRun[]>([]);
  const refreshRuns = useCallback(() => {
    listLiveRuns(projectId).then(setRuns).catch(() => setRuns([]));
  }, [projectId]);
  useEffect(() => { refreshRuns(); }, [refreshRuns]);
  useEffect(() => {
    if (live.status === "completed" || live.status === "failed") refreshRuns();
  }, [live.status, refreshRuns]);

  const staleRun = runs.find((r) => r.is_stale);

  async function onCancel(runId: string) {
    await cancelLiveRun(projectId, runId);
    refreshRuns();
  }

  return (
    <div className="space-y-4">
      <LiveSimulationControls disabled={streaming} onStart={live.start} />

      <div className="card space-y-3" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <LiveStatusBadge status={live.status} />
            {live.currentRound && <span className="text-xs text-slate-500">Round {live.currentRound}</span>}
          </div>
          {live.error && <span className="text-xs text-red-600">Error: {live.error}</span>}
        </div>
        <LiveProgressBar progress={live.progress} />

        {(live.status === "disconnected" || live.status === "failed") && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
            Stream interrupted. Persisted events (if any) are still saved · switch to <strong>Replay Mode</strong> to view them, or start again.
          </div>
        )}

        {live.status === "completed" && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-sm text-emerald-800">
            <span>Live run complete · {m.trial} trials, {m.recommend} recommends.</span>
            <button className="btn-secondary" onClick={onCompleted}>Replay saved events</button>
            <Link className="btn-secondary" to={`/projects/${projectId}/report`}>Generate Report</Link>
            <Link className="btn-secondary" to={`/projects/${projectId}/events`}>Event Explorer</Link>
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-5">
        <MetricCard label="Trials" value={String(m.trial)} tone="up" />
        <MetricCard label="Repeats" value={String(m.repeat)} tone="up" />
        <MetricCard label="Recommends" value={String(m.recommend)} tone="up" />
        <MetricCard label="Complaints" value={String(m.complaint)} tone="down" />
        <MetricCard label="Avg sentiment" value={m.sentN ? num(m.sentSum / m.sentN, 2) : "·"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <h2 className="mb-2 font-semibold text-slate-900">Agent network (live)</h2>
          <div className="relative">
            <AgentNetworkCanvas graph={graph} activeAgentId={live.activeAgentId} highlightAgentIds={new Set()} onSelect={onInspect} reducedMotion={reducedMotion} />
            {streaming && !reducedMotion && (
              <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2">
                <span className="inline-flex items-center gap-2 rounded-full bg-slate-900/85 px-3 py-1.5 text-xs font-medium text-white shadow-lg backdrop-blur">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                  </span>
                  Streaming live…
                </span>
              </div>
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">{graph.note}</p>
        </div>
        <div className="card">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold text-slate-900">Live event stream</h2>
            <label className="flex items-center gap-1 text-xs text-slate-500">
              Show latest
              <select className="input py-0.5 text-xs" value={streamCap} onChange={(e) => setStreamCap(Number(e.target.value))}>
                {[40, 100, 200].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
          <p className="mb-1 text-[10px] text-slate-400">Stream is capped for performance; metrics use the full revealed set.</p>
          <div className="max-h-[460px] space-y-2 overflow-y-auto" aria-label="Live event stream">
            {live.events.length === 0 ? (
              <div className="text-sm text-slate-400">Start a live simulation to watch events arrive…</div>
            ) : (
              live.events.slice(0, streamCap).map((e, i) => (
                <div key={`${e.event_id}-${i}`} className="rounded-lg border border-slate-200 bg-white p-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-800">{e.segment_name ?? titleCase(e.agent_type ?? "agent")}</span>
                    <span className="flex items-center gap-1">
                      <span className={`chip ${stanceMeta(e.sentiment_score).chip}`}>{stanceMeta(e.sentiment_score).label}</span>
                      <span className="chip border-brand-100 bg-brand-50 text-brand-700">{titleCase(e.action_type ?? "")}</span>
                    </span>
                  </div>
                  {e.generated_reaction && <div className="mt-1 italic text-slate-600">“{String(e.generated_reaction).slice(0, 130)}”</div>}
                  <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-slate-500">
                    <span>sentiment {num(e.sentiment_score, 2)}</span>
                    {e.trigger_detected && <span className="text-emerald-600">▲ {e.trigger_detected}</span>}
                    {e.barrier_detected && <span className="text-red-600">▼ {e.barrier_detected}</span>}
                    {e.agent_id && <button className="text-brand-700 hover:underline" onClick={() => onInspect(e.agent_id)}>Open agent</button>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {staleRun && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
          A previous live run is stuck (stale).{" "}
          <button className="font-medium underline" onClick={() => onCancel(staleRun.run_id)}>Mark stale / cancel</button>{" "}
          then start a new one.
        </div>
      )}

      <div className="card">
        <h2 className="mb-2 font-semibold text-slate-900">Live run history</h2>
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">No live runs yet.</p>
        ) : (
          <ul className="space-y-2" aria-label="Live run history">
            {runs.map((r) => (
              <li key={r.run_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className={`chip ${r.is_stale ? "border-amber-200 bg-amber-50 text-amber-700" : r.status === "completed" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : r.status === "failed" || r.status === "cancelled" ? "border-red-200 bg-red-50 text-red-700" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
                    {r.status}{r.is_stale ? " · stale" : ""}
                  </span>
                  <span className="text-slate-500">{r.total_events_emitted} events · {shortDate(r.created_at)}</span>
                </div>
                <div className="flex gap-2">
                  {r.can_replay_persisted_events && <button className="btn-secondary" onClick={onCompleted}>Open replay</button>}
                  {r.can_cancel && <button className="btn-danger" onClick={() => onCancel(r.run_id)}>Cancel</button>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
