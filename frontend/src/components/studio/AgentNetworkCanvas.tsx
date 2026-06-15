import { useMemo } from "react";
import type { StudioGraph, StudioNode } from "../../types/api";
import { stanceMeta } from "../../utils/formatters";

interface Pos {
  x: number;
  y: number;
}

const W = 1000;
const H = 620;
const CX = W / 2;
const CY = H / 2;
const R = 235;

function layout(nodes: StudioNode[]): Map<string, Pos> {
  const pos = new Map<string, Pos>();
  const groups = new Map<string, StudioNode[]>();
  for (const n of nodes) {
    const arr = groups.get(n.group) ?? [];
    arr.push(n);
    groups.set(n.group, arr);
  }
  const groupNames = [...groups.keys()].sort();
  const G = Math.max(1, groupNames.length);
  groupNames.forEach((g, gi) => {
    const angle = (gi / G) * Math.PI * 2 - Math.PI / 2;
    const gx = CX + R * Math.cos(angle);
    const gy = CY + R * Math.sin(angle);
    const members = groups.get(g)!;
    const k = members.length;
    const r = Math.min(78, 16 + k * 3.2);
    members.forEach((m, i) => {
      if (k === 1) {
        pos.set(m.id, { x: gx, y: gy });
      } else {
        const a = (i / k) * Math.PI * 2;
        pos.set(m.id, { x: gx + r * Math.cos(a), y: gy + r * Math.sin(a) });
      }
    });
  });
  return pos;
}

// Fill encodes stance (sentiment); active state overrides to amber.
function nodeColor(n: StudioNode, active: boolean): string {
  if (active) return "#f59e0b";
  return stanceMeta(n.avg_sentiment).fill;
}

const AGGREGATE_THRESHOLD = 150;

function edgeLabel(reason: string): string {
  if (!reason) return "";
  // Compact, relation-style token (e.g. "shared trigger: Less sugar" → "SHARED_TRIGGER").
  const head = reason.split(":")[0].trim();
  return head.replace(/[^a-zA-Z0-9]+/g, "_").toUpperCase().slice(0, 18);
}

export default function AgentNetworkCanvas({
  graph,
  activeAgentId,
  highlightAgentIds,
  onSelect,
  reducedMotion = false,
  showEdgeLabels = false,
  heightClass = "h-[480px]",
}: {
  graph: StudioGraph;
  activeAgentId: string | null;
  highlightAgentIds: Set<string>;
  onSelect: (agentId: string) => void;
  reducedMotion?: boolean;
  showEdgeLabels?: boolean;
  heightClass?: string;
}) {
  const aggregated = graph.nodes.length > AGGREGATE_THRESHOLD;
  const pos = useMemo(() => layout(graph.nodes), [graph.nodes]);

  const groups = useMemo(() => {
    const m = new Map<string, { count: number; x: number; y: number; type: string }>();
    for (const n of graph.nodes) {
      const p = pos.get(n.id);
      const g = m.get(n.group) ?? { count: 0, x: 0, y: 0, type: n.type };
      g.count += 1;
      if (p) { g.x += p.x; g.y += p.y; }
      m.set(n.group, g);
    }
    return [...m.entries()].map(([group, g]) => ({ group, count: g.count, x: g.x / g.count, y: g.y / g.count, type: g.type }));
  }, [graph.nodes, pos]);

  if (aggregated) {
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className={`${heightClass} w-full rounded-lg bg-slate-50`} role="img" aria-label="Agent network (segment clusters)">
        {groups.map((g) => {
          const r = Math.min(54, 14 + Math.sqrt(g.count) * 6);
          return (
            <g key={g.group} transform={`translate(${g.x},${g.y})`}>
              <circle r={r} fill={g.type === "market_actor" ? "#7c3aed" : "#2f5bea"} opacity={0.25} stroke="#fff" strokeWidth={1.5} />
              <text textAnchor="middle" dy={-2} fontSize={12} fontWeight={700} fill="#1e293b">{g.count}</text>
              <text textAnchor="middle" dy={14} fontSize={9} fill="#64748b">{g.group.slice(0, 16)}</text>
            </g>
          );
        })}
      </svg>
    );
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={`${heightClass} w-full rounded-lg bg-slate-50`} role="img" aria-label="Agent network">
      {/* edges */}
      <g stroke="#cbd5e1" strokeWidth={1}>
        {graph.edges.map((e, i) => {
          const a = pos.get(e.source);
          const b = pos.get(e.target);
          if (!a || !b) return null;
          const touches = e.source === activeAgentId || e.target === activeAgentId;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={touches ? "#f59e0b" : "#e2e8f0"}
              strokeWidth={touches ? 2 : 1}
              opacity={touches ? 0.9 : 0.45}
            >
              <title>{e.reason}</title>
            </line>
          );
        })}
      </g>
      {/* edge labels (toggle) */}
      {showEdgeLabels && (
        <g aria-hidden="true">
          {graph.edges.map((e, i) => {
            const a = pos.get(e.source);
            const b = pos.get(e.target);
            if (!a || !b) return null;
            const label = edgeLabel(e.reason);
            if (!label) return null;
            return (
              <text
                key={`l${i}`}
                x={(a.x + b.x) / 2}
                y={(a.y + b.y) / 2}
                textAnchor="middle"
                fontSize={6.5}
                fill="#94a3b8"
                style={{ pointerEvents: "none" }}
              >
                {label}
              </text>
            );
          })}
        </g>
      )}
      {/* nodes */}
      <g>
        {graph.nodes.map((n) => {
          const p = pos.get(n.id);
          if (!p) return null;
          const active = n.id === activeAgentId;
          const dim = highlightAgentIds.size > 0 && !highlightAgentIds.has(n.id) && !active;
          const isActor = n.type === "market_actor";
          const radius = isActor ? 11 : 7;
          // Market actors get a distinct purple ring so type stays legible while
          // fill encodes stance/sentiment.
          const stroke = active ? "#fff" : isActor ? "#7c3aed" : "#fff";
          const sw = isActor ? 2.5 : 1.5;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`} className="cursor-pointer" onClick={() => onSelect(n.id)} opacity={dim ? 0.25 : 1}>
              <circle r={active ? radius + 4 : radius} fill={nodeColor(n, active)} stroke={stroke} strokeWidth={sw} className={active && !reducedMotion ? "studio-pulse" : undefined}>
                <title>{`${n.label} — ${n.group} · ${stanceMeta(n.avg_sentiment).label} (${n.event_count} events)`}</title>
              </circle>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
