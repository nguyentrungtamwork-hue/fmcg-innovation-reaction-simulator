import { useState } from "react";
import { Link } from "react-router-dom";
import type { QAEvidenceRef } from "../types/api";
import { titleCase } from "../utils/formatters";

interface Props {
  ev: QAEvidenceRef;
  /** When provided, the expanded panel offers drill-down links into the Event Explorer / Agent Drawer. */
  projectId?: string;
}

export default function EvidenceChip({ ev, projectId }: Props) {
  const [open, setOpen] = useState(false);
  const eventHref = `/projects/${projectId}/events?event_id=${encodeURIComponent(ev.event_id)}&round_number=${ev.round_number}`;
  const agentHref = `/projects/${projectId}/events?agent_id=${encodeURIComponent(ev.agent_id)}&open_agent=1`;

  return (
    <div className="inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="chip border-brand-100 bg-brand-50 text-brand-700 hover:bg-brand-100"
        title={ev.short_reaction_excerpt}
        aria-expanded={open}
      >
        R{ev.round_number} · {titleCase(ev.action_type)}
        {ev.segment_name ? ` · ${ev.segment_name.split(" ")[0]}` : ""}
      </button>
      {open && (
        <div className="mt-1 max-w-md rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-600 shadow-sm">
          <div className="font-mono text-[10px] text-slate-400">event {ev.event_id}</div>
          {ev.segment_name && <div className="text-slate-500">{ev.segment_name}</div>}
          <div className="mt-1 italic">“{ev.short_reaction_excerpt}”</div>
          {projectId && (
            <div className="mt-2 flex gap-2">
              <Link className="font-medium text-brand-700 hover:underline" to={eventHref}>
                Open event →
              </Link>
              <Link className="font-medium text-brand-700 hover:underline" to={agentHref}>
                Open agent →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
