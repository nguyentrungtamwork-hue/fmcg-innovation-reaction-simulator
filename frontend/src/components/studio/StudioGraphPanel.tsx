import AgentNetworkCanvas from "./AgentNetworkCanvas";
import type { StudioGraph } from "../../types/api";
import { legendItems, type ColorBy } from "../../utils/formatters";

const COLOR_BY: { key: ColorBy; label: string }[] = [
  { key: "stance", label: "Stance" },
  { key: "type", label: "Type" },
  { key: "action", label: "Action" },
];

function Legend({ colorBy }: { colorBy: ColorBy }) {
  const items = legendItems(colorBy);
  const title = colorBy === "type" ? "Agent type" : colorBy === "action" ? "Dominant action" : "Stance";
  return (
    <div className="pointer-events-none absolute bottom-3 left-3 max-w-[250px] rounded-lg border border-slate-200 bg-white/92 p-3 text-[11px] text-slate-500 shadow-panel backdrop-blur" aria-label="Legend">
      <div className="mono-label mb-1.5 text-slate-500">{title}</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {items.map((it) => (
          <span key={it.label} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: it.fill }} /> {it.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: "#f59e0b" }} /> Active</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 border-t border-slate-100 pt-1.5">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-violet-600 bg-white" /> Market actor</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-slate-300 opacity-50" /> Filtered out</span>
      </div>
      <div className="mt-2 flex items-center gap-1.5 border-t border-slate-100 pt-1.5" title="Edges are derived from shared triggers/barriers/rounds, not direct conversations.">
        <span className="h-px w-4 bg-slate-400" /> Heuristic edge (shared signal, not a conversation)
      </div>
    </div>
  );
}

function LivePill() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2" aria-hidden="true">
      <span className="inline-flex items-center gap-2 rounded-full bg-ink-900/90 px-3 py-1.5 text-xs font-medium text-white shadow-panel backdrop-blur">
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
  colorBy,
  onColorBy,
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
  colorBy: ColorBy;
  onColorBy: (c: ColorBy) => void;
}) {
  return (
    <div className="card relative" data-tour="studio-canvas">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tightest text-slate-900">Agent Interaction Map</h2>
          <div className="mono-label mt-0.5">
            {graph.nodes.length} nodes · {graph.edges.length} edges
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* color-by taxonomy */}
          <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-0.5" role="group" aria-label="Color nodes by">
            {COLOR_BY.map((c) => (
              <button
                key={c.key}
                onClick={() => onColorBy(c.key)}
                aria-pressed={colorBy === c.key}
                className={`rounded-md px-2 py-1 text-xs font-medium transition ${colorBy === c.key ? "bg-white text-slate-900 shadow-card" : "text-slate-500 hover:text-slate-700"}`}
              >
                {c.label}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            <input
              type="checkbox"
              checked={showEdgeLabels}
              onChange={(e) => onToggleEdgeLabels(e.target.checked)}
              aria-label="Show edge labels"
              className="accent-brand-600"
            />
            Edge labels
          </label>
          <button className="btn-secondary py-1 text-xs" onClick={onRefresh} aria-label="Refresh map">Refresh</button>
          <button className="btn-secondary py-1 text-xs" onClick={onToggleExpand} aria-label={expanded ? "Exit fullscreen map" : "Expand map"}>
            {expanded ? "Split view" : "Expand"}
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
          colorBy={colorBy}
        />
        <Legend colorBy={colorBy} />
        {live && !reducedMotion && <LivePill />}
      </div>
      <p className="mt-2 text-[11px] text-slate-400">{graph.note}</p>
    </div>
  );
}
