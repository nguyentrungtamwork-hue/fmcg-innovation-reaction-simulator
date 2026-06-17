import { useEffect, useState } from "react";
import { getAgent } from "../api/agents";
import type { AgentOut } from "../types/api";
import { num, titleCase } from "../utils/formatters";
import { useFocusTrap } from "../hooks/useFocusTrap";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";

interface Props {
  projectId: string;
  agentId: string | null;
  onClose: () => void;
}

const TRAIT_KEYS = [
  "price_sensitivity",
  "novelty_seeking_level",
  "brand_loyalty_level",
  "claim_skepticism_level",
  "health_safety_concern_level",
  "convenience_need_level",
  "taste_or_sensory_importance",
  "packaging_sensitivity",
  "promotion_sensitivity",
  "social_influence_sensitivity",
  "review_dependency_level",
];

function strList(profile: Record<string, unknown>, key: string): string[] {
  const v = profile[key];
  return Array.isArray(v) ? v.map((x) => String(x)) : [];
}

function memList(value: unknown[]): string[] {
  return value.map((x) => (typeof x === "string" ? x : JSON.stringify(x)));
}

export default function AgentDrawer({ projectId, agentId, onClose }: Props) {
  const [agent, setAgent] = useState<AgentOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const trapRef = useFocusTrap<HTMLDivElement>(!!agentId);

  useEffect(() => {
    if (!agentId) return;
    setLoading(true);
    setError(null);
    setAgent(null);
    getAgent(projectId, agentId)
      .then(setAgent)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [projectId, agentId]);

  useEffect(() => {
    if (!agentId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [agentId, onClose]);

  if (!agentId) return null;
  const p = agent?.profile ?? {};

  return (
    <div ref={trapRef} tabIndex={-1} className="fixed inset-0 z-40 flex" role="dialog" aria-modal="true" aria-label="Agent detail">
      <button className="flex-1 bg-slate-900/40" aria-label="Close drawer" onClick={onClose} />
      <aside className="h-full w-full max-w-md overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-xl sm:w-[28rem]">
        <div className="mb-3 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{agent?.name ?? "Agent"}</h2>
            <p className="text-xs text-slate-500">
              {agent ? `${titleCase(agent.agent_type)} · ${agent.segment_name ?? agent.role ?? "·"}` : ""}
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {loading && <LoadingState label="Loading agent…" />}
        {error ? <ErrorState error={error} /> : null}

        {agent && (
          <div className="space-y-4 text-sm">
            <div>
              <div className="label">Key traits</div>
              <div className="grid grid-cols-2 gap-1.5">
                {TRAIT_KEYS.filter((k) => typeof p[k] === "number").map((k) => (
                  <div key={k} className="rounded border border-slate-200 px-2 py-1">
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">{titleCase(k)}</div>
                    <div className="font-medium text-slate-700">{num(p[k] as number, 2)}</div>
                  </div>
                ))}
              </div>
            </div>

            <DrawerList title="Trust drivers" items={strList(p, "trust_drivers")} />
            <DrawerList title="Trial barriers" items={strList(p, "trial_barriers")} />
            <DrawerList title="Repeat purchase drivers" items={strList(p, "repeat_purchase_drivers")} />
            <DrawerList title="Likely objections" items={strList(p, "likely_objections")} />
            <DrawerList title="Grounding sources" items={strList(p, "grounding_sources")} />
            <DrawerList title="Initial memory" items={memList(agent.memory)} />
            <DrawerList title="Simulation memory" items={memList(agent.simulation_memory)} />
            <DrawerList title="Action history" items={memList(agent.action_history)} />

            <div className="font-mono text-[10px] text-slate-400">agent {agent.id}</div>
          </div>
        )}
      </aside>
    </div>
  );
}

function DrawerList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <div className="label">{title}</div>
      <ul className="list-inside list-disc space-y-1 text-xs text-slate-600">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}
