import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { comparePortfolio, getPortfolio } from "../api/portfolio";
import type { CompareOut, PortfolioProjectRow } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import ScorecardCard from "../components/ScorecardCard";

const ROWS: { key: keyof import("../types/api").Scorecard; label: string; risk?: boolean }[] = [
  { key: "overall_score", label: "Overall" },
  { key: "trial_potential_score", label: "Trial" },
  { key: "repeat_potential_score", label: "Repeat" },
  { key: "confidence_score", label: "Confidence" },
  { key: "risk_score", label: "Risk", risk: true },
  { key: "claim_credibility_score", label: "Claim credibility" },
  { key: "price_value_score", label: "Price/value" },
  { key: "channel_fit_score", label: "Channel fit" },
  { key: "assumption_risk_score", label: "Assumption risk", risk: true },
  { key: "sensitivity_risk_score", label: "Sensitivity risk", risk: true },
];

export default function ComparePage() {
  const [available, setAvailable] = useState<PortfolioProjectRow[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<CompareOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    getPortfolio()
      .then((p) => setAvailable(p.projects.filter((x) => x.has_report)))
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length < 5 ? [...s, id] : s));
  }

  async function run() {
    setComparing(true);
    setError(null);
    try {
      setResult(await comparePortfolio({ project_ids: selected }));
    } catch (e) {
      setError(e);
    } finally {
      setComparing(false);
    }
  }

  if (loading) return <LoadingState label="Loading concepts…" />;

  const best = result?.comparison_summary;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Compare concepts</h1>
          <p className="text-sm text-slate-500">Select 2·5 report-ready concepts to compare side by side.</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to="/portfolio/decision-board">Decision Board</Link>
          <Link className="btn-secondary" to="/portfolio">← Portfolio</Link>
        </div>
      </div>

      {error ? <ErrorState error={error} /> : null}

      <div className="card space-y-3">
        {available.length === 0 ? (
          <p className="text-sm text-slate-500">No report-ready concepts yet. Generate a report for at least two projects.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {available.map((p) => (
              <label
                key={p.project_id}
                className={`chip cursor-pointer ${selected.includes(p.project_id) ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
              >
                <input type="checkbox" className="accent-brand-600" checked={selected.includes(p.project_id)} onChange={() => toggle(p.project_id)} />
                {p.project_name}
              </label>
            ))}
          </div>
        )}
        <button className="btn-primary" disabled={comparing || selected.length < 2} onClick={run}>
          {comparing ? "Comparing…" : `Compare ${selected.length || ""}`}
        </button>
      </div>

      {result && result.items.length > 0 && (
        <div className="space-y-5">
          <div className="card">
            <div className="label">Recommendation</div>
            <p className="text-sm text-slate-700">{result.recommendation}</p>
            {best && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {best.best_overall && <span className="chip border-emerald-200 bg-emerald-50 text-emerald-700">Best overall: {best.best_overall}</span>}
                {best.best_trial && <span className="chip border-slate-200 bg-slate-50 text-slate-600">Best trial: {best.best_trial}</span>}
                {best.best_repeat && <span className="chip border-slate-200 bg-slate-50 text-slate-600">Best repeat: {best.best_repeat}</span>}
                {best.lowest_risk && <span className="chip border-slate-200 bg-slate-50 text-slate-600">Lowest risk: {best.lowest_risk}</span>}
                {best.highest_confidence && <span className="chip border-slate-200 bg-slate-50 text-slate-600">Highest confidence: {best.highest_confidence}</span>}
                {best.most_needs_validation && <span className="chip border-amber-200 bg-amber-50 text-amber-700">Needs validation: {best.most_needs_validation}</span>}
              </div>
            )}
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-2">Dimension</th>
                  {result.items.map((it) => (
                    <th key={it.name} className="px-2 text-right">{it.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((r) => {
                  const vals = result.items.map((it) => Number(it.scorecard[r.key]));
                  const best = r.risk ? Math.min(...vals) : Math.max(...vals);
                  return (
                    <tr key={String(r.key)} className="border-b border-slate-100">
                      <td className="py-1 pr-2 text-slate-600">{r.label}{r.risk ? " ↓" : ""}</td>
                      {result.items.map((it, idx) => {
                        const v = vals[idx];
                        const isBest = v === best;
                        const display = r.key === "confidence_score" ? v.toFixed(2) : v;
                        return (
                          <td key={it.name} className={`px-2 text-right ${isBest ? "font-bold text-emerald-700" : "text-slate-700"}`}>
                            {display}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {result.items.map((it) => (
              <ScorecardCard key={it.name} sc={it.scorecard} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
