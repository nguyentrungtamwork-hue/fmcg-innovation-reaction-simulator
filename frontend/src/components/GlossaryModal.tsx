import { useEffect, useMemo, useState } from "react";
import { useFocusTrap } from "../hooks/useFocusTrap";

type Cat = "Simulation" | "Research" | "Reporting" | "Operations";

// [term, definition, category, optional link]
const TERMS: [string, string, Cat, string?][] = [
  ["Ontology", "The structured FMCG map extracted from the brief · entities (brand, claims, segments, channels…) + relationships, triggers, barriers, and risks.", "Simulation"],
  ["Agent", "A simulated consumer persona with traits, memory, and reactions across the 6 launch rounds.", "Simulation"],
  ["Market actor", "A non-consumer actor (Retailer, Competitor, Influencer, Community, Category Expert) that reacts to the launch each round.", "Simulation"],
  ["Simulation event", "One agent's action + reasoning in a round (e.g. purchase_trial, complain), with scores like sentiment and trial probability.", "Simulation"],
  ["Live Simulation", "Watching the simulation generate events in real time over SSE (Live Mode).", "Simulation"],
  ["Replay vs Live Mode", "Replay animates already-saved events client-side; Live Mode streams a new run as the backend generates + persists it.", "Simulation"],
  ["Trial probability", "Modelled likelihood an agent tries the product. Higher is better.", "Research"],
  ["Repeat probability", "Modelled likelihood an agent buys again after trial · the tightest part of the funnel.", "Research"],
  ["Evidence chip", "A clickable reference to a specific simulated event that backs a finding; opens the Event Explorer / Agent Drawer.", "Research"],
  ["Scenario", "A what-if re-run under lever overrides (price, sampling, claim credibility…). The baseline is always preserved.", "Research"],
  ["Sensitivity sweep", "Running a lever across several values to see the trial/repeat response curve · how responsive the launch is.", "Research"],
  ["Confidence", "A heuristic 0·1 score of internal data coverage/grounding · NOT validation against the real market.", "Research"],
  ["Assumptions ledger", "Everything the simulation assumes (data gaps, modelling caveats, simulated personas) with impact + how to validate.", "Research"],
  ["Scorecard", "A transparent 0·100 concept heuristic combining trial, repeat, sentiment, risk, confidence, etc. (see SCORING_LOGIC).", "Reporting"],
  ["Snapshot", "An immutable, named freeze of a report + scorecard so a decision is preserved when the project changes.", "Reporting"],
  ["Diff", "A comparison of two report versions (or active vs snapshot) showing per-dimension deltas and what changed.", "Reporting"],
  ["Briefing", "An evidence-grounded executive narrative: recommendation, findings, risks, next actions, validation plan.", "Reporting"],
  ["Sample library", "Ready-made fictional FMCG concepts you can load as a new project to explore the workflow.", "Operations", "/samples"],
  ["Export bundle", "A single no-secret JSON file containing a whole project, for backup or sharing. Import recreates it as a new project.", "Operations", "/data-tools"],
  ["Diagnostics", "A read-only drawer with backend status, DB counts, recent errors and request IDs for troubleshooting.", "Operations"],
];

const CATEGORIES: ("All" | Cat)[] = ["All", "Simulation", "Research", "Reporting", "Operations"];

export default function GlossaryModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const trapRef = useFocusTrap<HTMLDivElement>(open);
  const [query, setQuery] = useState("");
  const [cat, setCat] = useState<"All" | Cat>("All");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return TERMS.filter(([term, def, category]) => {
      if (cat !== "All" && category !== cat) return false;
      if (!q) return true;
      return `${term} ${def}`.toLowerCase().includes(q);
    });
  }, [query, cat]);

  if (!open) return null;
  return (
    <div ref={trapRef} tabIndex={-1} className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Glossary">
      <button className="flex-1 bg-slate-900/40" aria-label="Close glossary" onClick={onClose} />
      <aside className="h-full w-full max-w-md overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Glossary</h2>
          <button className="btn-secondary" onClick={onClose}>✕</button>
        </div>
        <label htmlFor="glossary-search" className="sr-only">Search glossary</label>
        <input
          id="glossary-search"
          className="input mb-2 py-1 text-sm"
          placeholder="Search terms…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="mb-3 flex flex-wrap gap-1" role="tablist" aria-label="Glossary categories">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              role="tab"
              aria-selected={cat === c}
              className={`chip ${cat === c ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}
              onClick={() => setCat(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <dl className="space-y-3">
          {filtered.length === 0 ? (
            <p className="text-xs text-slate-400">No terms match your search.</p>
          ) : (
            filtered.map(([term, def, , link]) => (
              <div key={term}>
                <dt className="text-sm font-semibold text-slate-800">{term}</dt>
                <dd className="text-xs text-slate-600">
                  {def}{" "}
                  {link && <a className="text-brand-700 underline" href={link} onClick={onClose}>Open →</a>}
                </dd>
              </div>
            ))
          )}
        </dl>
        <p className="mt-4 text-[11px] text-slate-400">Exploratory decision support · simulated reactions, not a guaranteed forecast.</p>
      </aside>
    </div>
  );
}
