import { useEffect, useState } from "react";
import { getAssumptions } from "../api/insights";
import type { AssumptionsOut } from "../types/api";
import { downloadText, titleCase } from "../utils/formatters";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";

const impactClass: Record<string, string> = {
  high: "border-red-200 bg-red-50 text-red-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  low: "border-slate-200 bg-slate-50 text-slate-500",
};

export default function AssumptionsLedger({ projectId }: { projectId: string }) {
  const [data, setData] = useState<AssumptionsOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAssumptions(projectId)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <section className="card"><LoadingState label="Loading assumptions…" /></section>;
  if (error) return <section className="card"><ErrorState error={error} /></section>;
  if (!data) return null;

  return (
    <section className="card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold text-slate-900">Assumptions ledger</h2>
        <div className="flex items-center gap-2 print:hidden">
          <span className="chip border-red-200 bg-red-50 text-red-700">{data.summary.high_impact_count} high</span>
          <span className="chip border-amber-200 bg-amber-50 text-amber-700">{data.summary.medium_impact_count} med</span>
          <span className="chip border-slate-200 bg-slate-50 text-slate-500">{data.summary.low_impact_count} low</span>
          <button
            className="btn-secondary"
            onClick={() => downloadText(`fmcg-assumptions-${projectId}.json`, JSON.stringify(data, null, 2), "application/json")}
          >
            Download JSON
          </button>
        </div>
      </div>
      <p className="mb-3 text-xs text-slate-500">What the simulation assumed and what still needs real-world validation.</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-2">Category</th>
              <th className="px-2">Assumption</th>
              <th className="px-2">Impact</th>
              <th className="px-2">Recommended validation</th>
            </tr>
          </thead>
          <tbody>
            {data.assumptions.map((a, i) => (
              <tr key={i} className="border-b border-slate-100 align-top">
                <td className="py-2 pr-2 text-slate-600">{titleCase(a.category)}</td>
                <td className="px-2 text-slate-700">{a.assumption}</td>
                <td className="px-2">
                  <span className={`chip ${impactClass[a.impact] ?? impactClass.low}`}>{a.impact}</span>
                </td>
                <td className="px-2 text-xs text-slate-600">{a.recommended_validation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
