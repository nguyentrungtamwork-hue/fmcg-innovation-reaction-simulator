import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport, getReportMarkdown } from "../api/reports";
import type { ReportGenerateOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import { downloadText, num, pct, titleCase } from "../utils/formatters";
import ConfidencePanel from "../components/ConfidencePanel";
import AssumptionsLedger from "../components/AssumptionsLedger";
import EvidenceChip from "../components/EvidenceChip";
import SnapshotPanel from "../components/SnapshotPanel";
import DriftIndicator from "../components/DriftIndicator";

export default function ReportPage() {
  const { projectId = "" } = useParams();
  const [report, setReport] = useState<ReportGenerateOut | null>(null);
  const [markdown, setMarkdown] = useState<string>("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [showMd, setShowMd] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getReport(projectId)
      .then((r) => {
        setReport(r);
        return getReportMarkdown(projectId);
      })
      .then((md) => setMarkdown(md))
      .catch((e) => setError(e))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <LoadingState label="Loading report…" />;
  if (error)
    return (
      <div className="space-y-3">
        <ErrorState error={error} />
        <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/workflow`}>
          ← Back to workflow
        </Link>
      </div>
    );
  if (!report) return null;

  const rp = report.report_payload;
  const es = rp.executive_summary;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Strategic launch report</h1>
          <p className="text-sm text-slate-500">
            {report.source_mode} · confidence {pct(report.confidence_score)} · generated {new Date(report.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 print:hidden">
          <Link className="btn-secondary" to={`/projects/${projectId}/events`}>
            Event explorer
          </Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/studio`}>
            Agent Studio
          </Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/sensitivity`}>
            Sensitivity
          </Link>
          <Link className="btn-primary" to={`/projects/${projectId}/briefing`}>
            Executive briefing
          </Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/decision-pack`}>
            Decision Pack
          </Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/snapshots/diff`}>
            Snapshot diff
          </Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/decisions`}>
            History
          </Link>
          <button className="btn-secondary" onClick={() => setShowMd((v) => !v)}>
            {showMd ? "Hide" : "Show"} markdown
          </button>
          <button
            className="btn-secondary"
            onClick={() => downloadText(`fmcg-innovation-report-${projectId}.md`, markdown, "text/markdown")}
          >
            Download Markdown
          </button>
          <button
            className="btn-secondary"
            onClick={() =>
              downloadText(
                `fmcg-innovation-report-${projectId}.json`,
                JSON.stringify(report.report_payload, null, 2),
                "application/json"
              )
            }
          >
            Download JSON
          </button>
          <button className="btn-primary" onClick={() => window.print()}>
            Print report
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
        Exploratory decision support — simulated reactions, not a guaranteed forecast. Validate findings with real consumer research.
      </div>

      <DriftIndicator projectId={projectId} />

      {/* executive summary */}
      <section className="card space-y-3">
        <h2 className="font-semibold text-slate-900">Executive summary</h2>
        <p className="text-sm text-slate-700">{es.overall_market_reaction}</p>
        <div className="grid gap-3 md:grid-cols-2">
          <Fact label="Top opportunity" value={es.top_opportunity} tone="emerald" />
          <Fact label="Top risk" value={es.top_risk} tone="red" />
          <Fact label="Estimated trial potential" value={es.estimated_trial_potential} />
          <Fact label="Estimated repeat potential" value={es.estimated_repeat_potential} />
        </div>
        <Fact label="Key recommendation" value={es.key_recommendation} tone="brand" />
      </section>

      {/* concept scorecard + snapshots */}
      <SnapshotPanel projectId={projectId} />

      {/* confidence calibration */}
      <ConfidencePanel projectId={projectId} />

      {/* segment reaction map */}
      <section className="card">
        <h2 className="mb-3 font-semibold text-slate-900">Segment reaction map</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">Segment</th>
                <th className="px-3">Agents</th>
                <th className="px-3">Trial</th>
                <th className="px-3">Intent</th>
                <th className="px-3">Repeat</th>
                <th className="px-3">Strongest trigger</th>
                <th className="px-3">Strongest barrier</th>
              </tr>
            </thead>
            <tbody>
              {rp.segment_reaction_map.map((s) => (
                <tr key={s.segment_name} className="border-b border-slate-100">
                  <td className="py-2 pr-3 font-medium text-slate-800">{s.segment_name}</td>
                  <td className="px-3">{s.number_of_agents}</td>
                  <td className="px-3">{pct(s.average_trial_probability)}</td>
                  <td className="px-3">{pct(s.average_purchase_intent_score)}</td>
                  <td className="px-3">{pct(s.average_repeat_probability)}</td>
                  <td className="px-3 text-emerald-700">{s.strongest_trigger ?? "—"}</td>
                  <td className="px-3 text-red-700">{s.strongest_barrier ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* triggers + barriers */}
      <div className="grid gap-5 md:grid-cols-2">
        <section className="card">
          <h2 className="mb-3 font-semibold text-slate-900">Top purchase triggers</h2>
          <ul className="space-y-2 text-sm">
            {rp.purchase_trigger_analysis.slice(0, 5).map((t, i) => (
              <li key={i} className="rounded-lg border border-emerald-100 bg-emerald-50 p-2">
                <div className="flex justify-between font-medium text-emerald-800">
                  <span>{t.trigger}</span>
                  <span>×{t.frequency}</span>
                </div>
                <div className="text-xs text-slate-600">{t.strategic_implication}</div>
                {t.evidence_events.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1 print:hidden">
                    {t.evidence_events.slice(0, 3).map((ev) => (
                      <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2 className="mb-3 font-semibold text-slate-900">Top adoption barriers</h2>
          <ul className="space-y-2 text-sm">
            {rp.adoption_barrier_analysis.slice(0, 5).map((b, i) => (
              <li key={i} className="rounded-lg border border-red-100 bg-red-50 p-2">
                <div className="flex justify-between font-medium text-red-800">
                  <span>{b.barrier}</span>
                  <span className="text-xs">×{b.frequency} · {b.severity_level}</span>
                </div>
                <div className="text-xs text-slate-600">Fix: {b.recommended_fix}</div>
                {b.evidence_events.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1 print:hidden">
                    {b.evidence_events.slice(0, 3).map((ev) => (
                      <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* trial & repeat */}
      <section className="card">
        <h2 className="mb-3 font-semibold text-slate-900">Trial &amp; repeat forecast</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <Fact label="Likely triers" value={rp.trial_repeat_forecast.likely_triers} />
          <Fact label="Likely repeaters" value={rp.trial_repeat_forecast.likely_repeaters} />
          <Fact label="One-time trial risk" value={rp.trial_repeat_forecast.one_time_trial_risk} tone="amber" />
          <Fact label="Promotion dependency" value={rp.trial_repeat_forecast.dependency_on_promotion} />
        </div>
      </section>

      {/* risk matrix */}
      <section className="card">
        <h2 className="mb-3 font-semibold text-slate-900">Innovation risk matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">Risk</th>
                <th className="px-3">Severity</th>
                <th className="px-3">Mitigation</th>
              </tr>
            </thead>
            <tbody>
              {rp.innovation_risk_matrix.map((r, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-2 pr-3 font-medium text-slate-800">{r.risk_type}</td>
                  <td className="px-3">
                    <SeverityChip level={r.severity} />
                  </td>
                  <td className="px-3 text-slate-600">{r.mitigation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* recommendations */}
      <section className="card">
        <h2 className="mb-3 font-semibold text-slate-900">Strategic recommendations</h2>
        <ul className="space-y-2 text-sm">
          {rp.strategic_recommendations.map((r, i) => (
            <li key={i} className="rounded-lg border border-slate-200 p-2">
              <span className="chip mr-2 border-brand-100 bg-brand-50 text-brand-700">{r.priority}</span>
              <span className="font-medium text-slate-800">{r.recommendation}</span>
              <span className="ml-1 text-xs text-slate-500">({r.owner_team})</span>
              <div className="mt-1 text-xs text-slate-600">{r.rationale}</div>
            </li>
          ))}
        </ul>
      </section>

      {/* A/B tests */}
      <section className="card">
        <h2 className="mb-3 font-semibold text-slate-900">Recommended A/B tests</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {rp.recommended_ab_tests.map((t, i) => (
            <div key={i} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="font-medium text-slate-800">{t.test_name}</div>
              <div className="mt-1 text-xs text-slate-600">A: {t.variant_a}</div>
              <div className="text-xs text-slate-600">B: {t.variant_b}</div>
              <div className="mt-1 text-xs text-slate-500">Metric: {t.success_metric}</div>
            </div>
          ))}
        </div>
      </section>

      {/* markdown preview */}
      {showMd && (
        <section className="card">
          <h2 className="mb-3 font-semibold text-slate-900">Markdown report</h2>
          <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
            {markdown}
          </pre>
        </section>
      )}

      {/* assumptions ledger */}
      <AssumptionsLedger projectId={projectId} />

      <Link className="btn-secondary inline-flex print:hidden" to={`/projects/${projectId}/workflow`}>
        ← Back to workflow
      </Link>
    </div>
  );
}

function Fact({ label, value, tone = "slate" }: { label: string; value: string; tone?: string }) {
  const toneMap: Record<string, string> = {
    slate: "border-slate-200 bg-white",
    emerald: "border-emerald-200 bg-emerald-50",
    red: "border-red-200 bg-red-50",
    amber: "border-amber-200 bg-amber-50",
    brand: "border-brand-200 bg-brand-50",
  };
  return (
    <div className={`rounded-lg border p-3 ${toneMap[tone]}`}>
      <div className="label">{label}</div>
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}

function SeverityChip({ level }: { level: string }) {
  const map: Record<string, string> = {
    high: "border-red-200 bg-red-50 text-red-700",
    medium: "border-amber-200 bg-amber-50 text-amber-700",
    low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
  return <span className={`chip ${map[level] ?? "border-slate-200 bg-slate-50 text-slate-600"}`}>{titleCase(level)}</span>;
}
