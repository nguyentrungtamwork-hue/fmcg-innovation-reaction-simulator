import { Link } from "react-router-dom";
import type { StudioEvent } from "../../types/api";
import { num, titleCase, stanceMeta } from "../../utils/formatters";

interface Props {
  projectId: string;
  events: StudioEvent[]; // newest first, already capped
  onInspect: (agentId: string) => void;
}

function sentimentTone(v: number | null): string {
  if (v === null) return "text-slate-500";
  return v > 0.15 ? "text-emerald-600" : v < -0.05 ? "text-red-600" : "text-slate-500";
}

export default function LiveEventStream({ projectId, events, onInspect }: Props) {
  if (events.length === 0) {
    return <div className="text-sm text-slate-400">Press Play to stream reactions…</div>;
  }
  return (
    <ul className="space-y-2" aria-label="Live event stream">
      {events.map((e) => (
        <li key={e.id} className="rounded-lg border border-slate-200 bg-white p-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-slate-800">
              R{e.round_number} · {e.segment_name ?? titleCase(e.agent_type)}
            </span>
            <span className="flex items-center gap-1">
              <span className={`chip ${stanceMeta(e.sentiment_score).chip}`}>{stanceMeta(e.sentiment_score).label}</span>
              <span className="chip border-brand-100 bg-brand-50 text-brand-700">{titleCase(e.action_type)}</span>
            </span>
          </div>
          {e.generated_reaction && <div className="mt-1 italic text-slate-600">“{e.generated_reaction.slice(0, 140)}”</div>}
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
            <span className={sentimentTone(e.sentiment_score)}>sentiment {num(e.sentiment_score, 2)}</span>
            <span className="text-slate-400">conf {num(e.confidence_score, 2)}</span>
            {e.trigger_detected && <span className="text-emerald-600">▲ {e.trigger_detected}</span>}
            {e.barrier_detected && <span className="text-red-600">▼ {e.barrier_detected}</span>}
          </div>
          <div className="mt-1 flex gap-2">
            <button className="font-medium text-brand-700 hover:underline" onClick={() => onInspect(e.agent_id)}>
              Open agent
            </button>
            <Link className="font-medium text-brand-700 hover:underline" to={`/projects/${projectId}/events?event_id=${e.id}&round_number=${e.round_number}`}>
              Open event
            </Link>
            <button
              className="font-medium text-slate-500 hover:underline"
              onClick={() => {
                const text = `R${e.round_number} ${e.segment_name ?? e.agent_type} · ${e.action_type} · sentiment ${num(e.sentiment_score, 2)}${e.generated_reaction ? ` · "${e.generated_reaction}"` : ""} (event ${e.id})`;
                navigator.clipboard?.writeText(text).catch(() => {});
              }}
            >
              Copy evidence
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
