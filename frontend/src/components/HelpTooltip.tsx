import { useEffect, useId, useRef, useState } from "react";

/** Short, business-friendly help copy keyed by term (Phase 26). */
export const HELP_TEXT: Record<string, string> = {
  ontology: "The structured map of your concept — claims, benefits, segments, occasions and risks — extracted from the brief. It grounds everything downstream.",
  agent: "A simulated consumer persona built from a market segment. Agents react to your concept round by round.",
  market_actor: "A simulated non-consumer (e.g. retailer, competitor) whose actions can shift the launch context.",
  simulation_event: "One simulated reaction: what an agent saw, did, and felt, with scores like sentiment and trial probability.",
  live_mode: "Streams the simulation as it runs, round by round, so you can watch reactions form in real time.",
  replay_mode: "Plays back a completed run's saved events at your own pace — no re-computation.",
  trial_probability: "Modelled likelihood an agent tries the product at least once. A first-purchase signal, not a sales forecast.",
  repeat_probability: "Modelled likelihood an agent buys again after trying — the durability signal behind long-term success.",
  confidence: "How much trust to place in a result, based on evidence strength and agreement across agents. Not statistical significance.",
  assumptions: "The explicit modelling assumptions behind a result. Review them before acting on a number.",
  snapshot: "A frozen copy of a report + scorecard at a point in time, so you can compare how thinking changed.",
  scenario: "A what-if rerun with levers changed (price, sampling, claim credibility…). The baseline is never touched.",
  briefing: "An executive-ready summary of findings, risks, and recommended actions, tailored by audience.",
  export_bundle: "A single no-secret JSON file containing a whole project, for backup or sharing. Import recreates it as a new project.",
};

export default function HelpTooltip({ term, text, label }: { term?: keyof typeof HELP_TEXT | string; text?: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const id = useId();
  const content = text ?? (term ? HELP_TEXT[term] : "") ?? "";

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const onClick = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("mousedown", onClick); };
  }, [open]);

  if (!content) return null;

  return (
    <span ref={ref} className="relative inline-block align-middle">
      <button
        type="button"
        aria-label={label ? `Help: ${label}` : "Help"}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onClick={() => setOpen((v) => !v)}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 text-[10px] font-bold text-slate-500 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
      >
        ?
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute left-1/2 top-6 z-50 w-64 -translate-x-1/2 rounded-lg border border-slate-200 bg-white p-3 text-left text-xs font-normal leading-relaxed text-slate-600 shadow-lg"
        >
          {content}
        </span>
      )}
    </span>
  );
}
