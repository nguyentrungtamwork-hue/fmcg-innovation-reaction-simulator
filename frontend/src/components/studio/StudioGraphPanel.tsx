import AgentNetworkCanvas from "./AgentNetworkCanvas";
import type { StudioGraph } from "../../types/api";

function Legend() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-3 max-w-[244px] rounded-lg border border-slate-200 bg-white/90 p-3 text-[11px] text-slate-500 shadow-sm backdrop-blur" aria-label="Legend">
      <div className="mb-1 font-semibold uppercase tracking-wide text-rose-500">Stance</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: "#10b981" }} /> Advocate</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: "#64748b" }} /> Neutral</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: "#f43f5e" }} /> Skeptic</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: "#f59e0b" }} /> Active</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 border-t border-slate-100 pt-1.5">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-violet-600 bg-white" /> Market actor</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-slate-300 opacity-50" /> Filtered out</span>
      </div>
      <div className="mt-2 flex items-center gap-1.5 border-t border-slate-100 pt-1.5" title="Edges are derived from shared triggers/barriers/rounds, not direct conversations.">
        <span className="h-px w-4 bg-slate-400" /> Heuristic edge (shared trigger/barrier · not a conversation)
      </div>
    </div>
  );
}

function LivePill() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2" aria-hidden="true">
      <span className="inline-flex items-center gap-2 rounded-full bg-slate-900/85 px-3 py-1.5 text-xs font-medium text-white shadow-lg backdrop-blur">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
        </span>
        Updating in real-time…
      </span>
    </div>
  );
}

export default function StudioGraphPanel({
  graph,
  activeAgentId,
  highlightAgentIds,
  onSelect,
  reducedMotion,
  showEdgeLabels,
  onToggleEdgeLabels,
  onRefresh,
  expanded,
  onToggleExpand,
  live = false,
}: {
  graph: StudioGraph;
  activeAgentId: string | null;
  highlightAgentIds: Set<string>;
  onSelect: (agentId: string) => void;
  reducedMotion: boolean;
  showEdgeLabels: boolean;
  onToggleEdgeLabels: (v: boolean) => void;
  onRefresh: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
  /** show the floating "updating in real-time" pill (playback / live streaming) */
  live?: boolean;
}) {
  return (
    <div className="card relative" data-tour="studio-canvas">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold text-slate-900">Agent Interaction Map</h2>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            <input
              type="checkbox"
              checked={showEdgeLabels}
              onChange={(e) => onToggleEdgeLabels(e.target.checked)}
              aria-label="Show edge labels"
            />
            Show Edge Labels
          </label>
          <button className="btn-secondary py-1 text-xs" onClick={onRefresh} aria-label="Refresh map">↻ Refresh</button>
          <button className="btn-secondary py-1 text-xs" onClick={onToggleExpand} aria-label={expanded ? "Exit fullscreen map" : "Expand map"}>
            {expanded ? "⤡ Split" : "⤢ Expand"}
          </button>
        </div>
      </div>
      <div className="relative">
        <AgentNetworkCanvas
          graph={graph}
          activeAgentId={activeAgentId}
          highlightAgentIds={highlightAgentIds}
          onSelect={onSelect}
          reducedMotion={reducedMotion}
          showEdgeLabels={showEdgeLabels}
          heightClass={expanded ? "h-[640px]" : "h-[480px]"}
        />
        <Legend />
        {live && !reducedMotion && <LivePill />}
      </div>
      <p className="mt-2 text-[11px] text-slate-400">{graph.note}</p>
    </div>
  );
}
