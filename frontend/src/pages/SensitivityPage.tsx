import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { runSensitivity } from "../api/insights";
import type { LeverSweep, SensitivityOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import { MiniLineChart } from "../components/charts";
import { num, signed, titleCase } from "../utils/formatters";

const LEVERS: { key: string; label: string; values: number[] }[] = [
  { key: "price_change_pct", label: "Price change %", values: [0, -5, -10, -15] },
  { key: "sampling_boost", label: "Sampling boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "social_proof_boost", label: "Social proof boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "claim_credibility_boost", label: "Claim credibility boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "promotion_boost", label: "Promotion boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "packaging_appeal_boost", label: "Packaging appeal boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "sensory_risk_reduction", label: "Sensory risk reduction", values: [0, 0.05, 0.1, 0.15] },
  { key: "retailer_support_boost", label: "Retailer support boost", values: [0, 0.05, 0.1, 0.15] },
  { key: "competitor_pressure_boost", label: "Competitor pressure boost", values: [0, 0.05, 0.1, 0.15] },
];

const DEFAULT_SELECTED = ["price_change_pct", "sampling_boost", "social_proof_boost", "claim_credibility_boost"];

function trialLift(s: LeverSweep): number {
  if (!s.best_point || s.points.length === 0) return 0;
  return s.best_point.trial_probability - s.points[0].trial_probability;
}
function repeatLift(s: LeverSweep): number {
  if (s.points.length === 0) return 0;
  const max = Math.max(...s.points.map((p) => p.repeat_probability));
  return max - s.points[0].repeat_probability;
}
function worstTrial(s: LeverSweep): number {
  if (s.points.length === 0) return 0;
  return Math.min(...s.points.map((p) => p.trial_probability)) - s.points[0].trial_probability;
}

export default function SensitivityPage() {
  const { projectId = "" } = useParams();
  const [selected, setSelected] = useState<string[]>(DEFAULT_SELECTED);
  const [result, setResult] = useState<SensitivityOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  function toggle(key: string) {
    setSelected((s) => (s.includes(key) ? s.filter((k) => k !== key) : [...s, key]));
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const levers: Record<string, number[]> = {};
      LEVERS.filter((l) => selected.includes(l.key)).forEach((l) => (levers[l.key] = l.values));
      setResult(await runSensitivity(projectId, { levers, seed: 42, rounds: 6 }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  const sweeps = result?.sweeps ?? [];
  const bestTrial = sweeps.reduce<LeverSweep | null>((b, s) => (!b || trialLift(s) > trialLift(b) ? s : b), null);
  const bestRepeat = sweeps.reduce<LeverSweep | null>((b, s) => (!b || repeatLift(s) > repeatLift(b) ? s : b), null);
  const riskiest = sweeps.reduce<LeverSweep | null>((b, s) => (!b || worstTrial(s) < worstTrial(b) ? s : b), null);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Sensitivity sweep</h1>
          <p className="text-sm text-slate-500">How responsive is the launch to each lever? Deterministic; baseline is preserved.</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to={`/projects/${projectId}/scenarios`}>Scenario Lab</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/report`}>Report</Link>
        </div>
      </div>

      <div className="card space-y-3">
        <div className="label">Levers to sweep</div>
        <div className="flex flex-wrap gap-2">
          {LEVERS.map((l) => (
            <label
              key={l.key}
              className={`chip cursor-pointer ${selected.includes(l.key) ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
            >
              <input
                type="checkbox"
                className="accent-brand-600"
                checked={selected.includes(l.key)}
                onChange={() => toggle(l.key)}
              />
              {l.label}
            </label>
          ))}
        </div>
        <button className="btn-primary" disabled={loading || selected.length === 0} onClick={run}>
          {loading ? "Running sweep…" : "Run sensitivity sweep"}
        </button>
      </div>

      {loading && <LoadingState label="Running deterministic sweeps…" />}
      {error ? <ErrorState error={error} /> : null}

      {result && !loading && (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricCard
              label="Best trial lift"
              value={bestTrial ? signed(trialLift(bestTrial)) : "—"}
              hint={bestTrial ? titleCase(bestTrial.lever) : undefined}
              tone="up"
            />
            <MetricCard
              label="Best repeat lift"
              value={bestRepeat ? signed(repeatLift(bestRepeat)) : "—"}
              hint={bestRepeat ? titleCase(bestRepeat.lever) : undefined}
              tone="up"
            />
            <MetricCard
              label="Highest-risk lever"
              value={riskiest && worstTrial(riskiest) < -0.005 ? signed(worstTrial(riskiest)) : "—"}
              hint={riskiest ? titleCase(riskiest.lever) : undefined}
              tone="down"
            />
          </div>

          <div className="card">
            <div className="label">Recommended lever to test first</div>
            <p className="text-sm text-slate-700">{result.overall_recommendation}</p>
          </div>

          {sweeps.map((s) => (
            <div key={s.lever} className="card space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold text-slate-900">{titleCase(s.lever)}</h2>
                <span className="text-xs text-slate-500">{s.strategic_read}</span>
              </div>
              <MiniLineChart
                points={s.points.map((p) => ({
                  x: p.value,
                  y: p.trial_probability,
                  label: s.lever === "price_change_pct" ? `${p.value}%` : `${p.value}`,
                }))}
                width={420}
                height={110}
              />
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                      <th className="py-1 pr-2">Value</th>
                      <th className="px-2">Trial</th>
                      <th className="px-2">Repeat</th>
                      <th className="px-2">Sentiment</th>
                      <th className="px-2">Recommend</th>
                      <th className="px-2">Complaint</th>
                      <th className="px-2">Interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.points.map((p) => (
                      <tr key={p.value} className="border-b border-slate-100">
                        <td className="py-1 pr-2 font-medium">{s.lever === "price_change_pct" ? `${p.value}%` : `+${p.value}`}</td>
                        <td className="px-2">{num(p.trial_probability, 3)}</td>
                        <td className="px-2">{num(p.repeat_probability, 3)}</td>
                        <td className="px-2">{num(p.sentiment, 3)}</td>
                        <td className="px-2">{num(p.recommend_rate, 3)}</td>
                        <td className="px-2">{num(p.complaint_rate, 3)}</td>
                        <td className="px-2 text-xs text-slate-600">{p.interpretation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          <div className="card">
            <div className="label">Limitations</div>
            <ul className="list-inside list-disc space-y-1 text-xs text-slate-500">
              {result.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/workflow`}>← Back to workflow</Link>
    </div>
  );
}
