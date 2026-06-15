import { useState } from "react";
import { Link } from "react-router-dom";

const STORAGE_KEY = "onboarding_seen";

const STEPS: { label: string; to?: string; hint: string }[] = [
  { label: "Load a sample concept", to: "/samples", hint: "Start from a ready-made FMCG concept." },
  { label: "Analyze the ontology", hint: "Extract claims, segments and risks from the brief (Workflow step)." },
  { label: "Generate agents", hint: "Build simulated consumer + market-actor personas." },
  { label: "Run the live simulation", hint: "Watch reactions form round by round in Agent Studio." },
  { label: "Open Agent Studio", hint: "Inspect agents, replay events, and explore segments." },
  { label: "Generate the report", hint: "Get the 16-section strategic launch report." },
  { label: "Generate the briefing", hint: "Produce an executive-ready summary." },
  { label: "Export the project", to: "/data-tools", hint: "Back up or share the whole project as JSON." },
];

export function isOnboardingSeen(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export default function OnboardingPanel() {
  const [dismissed, setDismissed] = useState(isOnboardingSeen());

  function dismiss() {
    try { localStorage.setItem(STORAGE_KEY, "true"); } catch { /* ignore */ }
    setDismissed(true);
  }

  if (dismissed) return null;

  return (
    <section className="card border-brand-200 bg-brand-50" aria-labelledby="onboarding-h">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <h2 id="onboarding-h" className="text-base font-semibold text-slate-900">Welcome — get to your first insight in minutes</h2>
          <p className="text-sm text-slate-600">A quick guided path. You can dismiss this anytime; power users can ignore it.</p>
        </div>
        <button className="btn-secondary" onClick={dismiss} aria-label="Dismiss onboarding">Dismiss</button>
      </div>
      <ol className="grid gap-2 sm:grid-cols-2">
        {STEPS.map((s, i) => (
          <li key={s.label} className="flex items-start gap-2 rounded-lg border border-white/60 bg-white/70 p-2 text-sm">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600 text-[11px] font-bold text-white">{i + 1}</span>
            <span>
              {s.to ? <Link className="font-medium text-brand-700 underline" to={s.to}>{s.label}</Link> : <span className="font-medium text-slate-800">{s.label}</span>}
              <span className="block text-xs text-slate-500">{s.hint}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
