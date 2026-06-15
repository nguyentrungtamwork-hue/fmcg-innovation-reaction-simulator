import { useEffect, useState } from "react";
import { getConfidence } from "../api/insights";
import type { ConfidenceOut } from "../types/api";
import { ConfidenceGauge } from "./charts";
import { pct, titleCase } from "../utils/formatters";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";

export default function ConfidencePanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<ConfidenceOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getConfidence(projectId)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <section className="card"><LoadingState label="Loading confidence…" /></section>;
  if (error) return <section className="card"><ErrorState error={error} /></section>;
  if (!data) return null;

  return (
    <section className="card">
      <h2 className="mb-3 font-semibold text-slate-900">Confidence calibration</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="flex flex-col items-center justify-center">
          <ConfidenceGauge value={data.overall_confidence} label={data.confidence_label} />
          <div className="mt-1 text-xs text-slate-500">internal data-coverage score</div>
        </div>
        <div className="md:col-span-2">
          <div className="label">What drives this confidence</div>
          <ul className="space-y-1.5">
            {data.drivers.map((d) => (
              <li key={d.factor}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-700">{titleCase(d.factor)}</span>
                  <span className="text-slate-500">{pct(d.score)} · w{d.weight.toFixed(2)}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded bg-slate-100">
                  <div className="h-full rounded bg-brand-600" style={{ width: `${Math.round(d.score * 100)}%` }} />
                </div>
                <div className="text-[11px] text-slate-500">{d.explanation}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <div className="label">Confidence risks</div>
          <ul className="list-inside list-disc space-y-1 text-xs text-slate-600">
            {data.confidence_risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="label">How to improve confidence</div>
          <ul className="list-inside list-disc space-y-1 text-xs text-slate-600">
            {data.how_to_improve_confidence.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      </div>
      <p className="mt-3 text-[11px] text-slate-400">{data.disclaimer}</p>
    </section>
  );
}
