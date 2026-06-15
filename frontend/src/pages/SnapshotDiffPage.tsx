import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { listSnapshots } from "../api/portfolio";
import { createDecision, snapshotDiff } from "../api/history";
import type { DiffRequest, DiffSide, SnapshotDiffOut, SnapshotListItem } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import { MiniBarChart } from "../components/charts";
import { signed, titleCase } from "../utils/formatters";

const ACTIVE = "active";

function toSide(value: string): DiffSide {
  return value === ACTIVE ? { type: "active_report" } : { type: "snapshot", snapshot_id: value };
}

function tone(direction: string): "up" | "down" | "flat" {
  return direction === "improved" ? "up" : direction === "declined" ? "down" : "flat";
}

export default function SnapshotDiffPage() {
  const { projectId = "" } = useParams();
  const [params] = useSearchParams();
  const [snapshots, setSnapshots] = useState<SnapshotListItem[]>([]);
  const [left, setLeft] = useState<string>("");
  const [right, setRight] = useState<string>(ACTIVE);
  const [result, setResult] = useState<SnapshotDiffOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [logged, setLogged] = useState(false);

  useEffect(() => {
    listSnapshots(projectId)
      .then((s) => {
        setSnapshots(s);
        const preset = params.get("left");
        setLeft(preset && s.some((x) => x.snapshot_id === preset) ? preset : s[0]?.snapshot_id ?? ACTIVE);
      })
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function run() {
    setComparing(true);
    setError(null);
    setLogged(false);
    try {
      const req: DiffRequest = { left: toSide(left), right: toSide(right) };
      setResult(await snapshotDiff(projectId, req));
    } catch (e) {
      setError(e);
    } finally {
      setComparing(false);
    }
  }

  async function logDecision() {
    if (!result) return;
    await createDecision(projectId, {
      entry_type: "change",
      title: `Diff: ${result.left.name} → ${result.right.name}`,
      body: `${result.plain_english_summary} ${result.decision_implication}`,
      related_snapshot_id: left !== ACTIVE ? left : right !== ACTIVE ? right : null,
      tags: ["diff"],
    });
    setLogged(true);
  }

  if (loading) return <LoadingState label="Loading snapshots…" />;

  const sd = result?.scorecard_delta;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Snapshot diff</h1>
          <p className="text-sm text-slate-500">Compare two report versions and see what changed and why it matters.</p>
        </div>
        <Link className="btn-secondary" to={`/projects/${projectId}/report`}>← Report</Link>
      </div>

      {error ? <ErrorState error={error} /> : null}

      <div className="card flex flex-wrap items-end gap-3">
        <div>
          <label className="label" htmlFor="left">Left (baseline)</label>
          <select id="left" className="input min-w-[14rem] py-1" value={left} onChange={(e) => setLeft(e.target.value)}>
            <option value={ACTIVE}>Active report</option>
            {snapshots.map((s) => (
              <option key={s.snapshot_id} value={s.snapshot_id}>{s.snapshot_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="right">Right (compare)</label>
          <select id="right" className="input min-w-[14rem] py-1" value={right} onChange={(e) => setRight(e.target.value)}>
            <option value={ACTIVE}>Active report</option>
            {snapshots.map((s) => (
              <option key={s.snapshot_id} value={s.snapshot_id}>{s.snapshot_name}</option>
            ))}
          </select>
        </div>
        <button className="btn-primary" disabled={comparing} onClick={run}>{comparing ? "Comparing…" : "Compare"}</button>
      </div>

      {snapshots.length === 0 && (
        <div className="card text-sm text-slate-500">No snapshots yet. Create one from the Report page to compare against the active report.</div>
      )}

      {result && sd && (
        <div className="space-y-5">
          <div className="card">
            <div className="label">Summary</div>
            <p className="text-sm text-slate-800">{result.plain_english_summary}</p>
            <p className="mt-1 text-sm text-slate-600">{result.decision_implication}</p>
            <div className="mt-3 flex flex-wrap gap-2 print:hidden">
              <button className="btn-secondary" onClick={logDecision} disabled={logged}>
                {logged ? "Logged ✓" : "Create decision log from this diff"}
              </button>
              <Link className="btn-secondary" to={`/projects/${projectId}/decisions`}>Decision history →</Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            <MetricCard label="Overall Δ" value={signed(sd.overall_score.delta, 1)} tone={tone(result.dimension_changes.find((d) => d.dimension === "overall_score")?.direction ?? "flat")} />
            <MetricCard label="Trial Δ" value={signed(sd.trial_potential_score.delta, 1)} tone={tone(result.dimension_changes.find((d) => d.dimension === "trial_potential_score")?.direction ?? "flat")} />
            <MetricCard label="Repeat Δ" value={signed(sd.repeat_potential_score.delta, 1)} tone={tone(result.dimension_changes.find((d) => d.dimension === "repeat_potential_score")?.direction ?? "flat")} />
            <MetricCard label="Risk Δ" value={signed(sd.risk_score.delta, 1)} tone={tone(result.dimension_changes.find((d) => d.dimension === "risk_score")?.direction ?? "flat")} />
          </div>

          <div className="card">
            <div className="label">Dimension movements (magnitude)</div>
            <MiniBarChart
              width={520}
              height={120}
              bars={result.dimension_changes
                .filter((d) => Math.abs(d.delta) > 0.001)
                .slice(0, 8)
                .map((d) => ({ label: d.dimension.replace("_score", "").slice(0, 6), value: Math.abs(d.delta) }))}
            />
            <table className="mt-2 w-full text-left text-sm">
              <tbody>
                {result.dimension_changes.map((d) => (
                  <tr key={d.dimension} className="border-b border-slate-100">
                    <td className="py-1 pr-2 text-slate-600">{titleCase(d.dimension.replace("_score", ""))}</td>
                    <td className={`py-1 pr-2 text-right font-medium ${d.direction === "improved" ? "text-emerald-600" : d.direction === "declined" ? "text-red-600" : "text-slate-500"}`}>{signed(d.delta, 2)}</td>
                    <td className="py-1 text-xs text-slate-500">{d.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="card">
              <div className="label">Changed sections</div>
              <ul className="space-y-1 text-xs">
                {result.changed_sections.map((s) => (
                  <li key={s.section} className={s.change_type === "changed" ? "text-slate-700" : "text-slate-400"}>
                    {s.change_type === "changed" ? "● " : "○ "}{s.summary}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <div className="label">Risk changes</div>
              <RiskList title="Reduced / removed" items={result.risk_changes.reduced_risks} tone="emerald" />
              <RiskList title="New / increased" items={result.risk_changes.new_or_increased_risks} tone="red" />
            </div>
          </div>

          <div className="card">
            <div className="label">Recommended next step</div>
            <p className="text-xs text-slate-600">Left: {result.recommendation_changes.left_recommendation}</p>
            <p className="text-xs text-slate-600">Right: {result.recommendation_changes.right_recommendation}</p>
            <p className="mt-1 text-sm text-slate-700">{result.recommendation_changes.interpretation}</p>
          </div>

          {result.segment_changes.length > 0 && (
            <div className="card overflow-x-auto">
              <div className="label">Segment changes</div>
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-1 pr-2">Segment</th>
                    <th className="px-2 text-right">Trial Δ</th>
                    <th className="px-2 text-right">Repeat Δ</th>
                    <th className="px-2 text-right">Sentiment Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {result.segment_changes.map((s) => (
                    <tr key={s.segment_name} className="border-b border-slate-100">
                      <td className="py-1 pr-2 text-slate-700">{s.segment_name}</td>
                      <td className="px-2 text-right">{signed(s.trial_delta)}</td>
                      <td className="px-2 text-right">{signed(s.repeat_delta)}</td>
                      <td className="px-2 text-right">{signed(s.sentiment_delta)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RiskList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  const color = tone === "emerald" ? "text-emerald-700" : "text-red-700";
  return (
    <div className="mt-1">
      <div className={`text-xs font-semibold ${color}`}>{title}</div>
      <ul className="list-inside list-disc text-xs text-slate-600">
        {items.map((r, i) => <li key={i}>{r}</li>)}
      </ul>
    </div>
  );
}
