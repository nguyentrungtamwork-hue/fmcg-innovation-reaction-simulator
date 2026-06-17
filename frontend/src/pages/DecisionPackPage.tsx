import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getDecisionPack, getDecisionPackMarkdown } from "../api/projects";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import {
  CopyLinkButton,
  DecisionPackSection,
  DownloadJsonButton,
  DownloadMarkdownButton,
  PrintButton,
  ReadOnlyBadge,
} from "../components/decisionpack/DecisionPackParts";
import { titleCase } from "../utils/formatters";

type Pack = Record<string, any>;

export default function DecisionPackPage() {
  const { projectId = "" } = useParams();
  const [pack, setPack] = useState<Pack | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getDecisionPack(projectId).then(setPack).catch(setError).finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <LoadingState label="Building decision pack…" />;
  if (error) return <ErrorState error={error} />;
  if (!pack) return null;

  const h = pack.header ?? {};
  const es = pack.executive_summary ?? {};
  const sc = pack.scorecard ?? {};
  const name = String(h.project_name ?? "project").replace(/\s+/g, "_");

  return (
    <div className="decision-pack space-y-4">
      {/* Cover / header */}
      <div className="card decision-pack-section">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h1 className="text-2xl font-semibold text-slate-900">Decision Pack</h1>
              <ReadOnlyBadge />
            </div>
            <div className="text-lg font-medium text-slate-800">{h.project_name}</div>
            <div className="text-sm text-slate-500">
              {[h.concept_name, h.category].filter(Boolean).join(" · ")}
            </div>
            <div className="text-xs text-slate-400">Generated {String(pack.generated_at ?? "").slice(0, 10)}</div>
          </div>
          <div className="flex flex-wrap gap-2 print-hide">
            <PrintButton />
            <DownloadMarkdownButton getMarkdown={() => getDecisionPackMarkdown(projectId)} name={name} />
            <DownloadJsonButton data={pack} name={name} />
            <CopyLinkButton />
            <Link className="btn-secondary" to={`/projects/${projectId}/home`}>Back to Project Home</Link>
          </div>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <MetricCard label="Overall score" value={`${h.overall_score}/100`} tone="up" />
          <MetricCard label="Recommendation" value={titleCase(String(h.recommendation_status ?? ""))} />
          <MetricCard label="Confidence" value={String(h.confidence_label ?? "·")} />
        </div>
      </div>

      <DecisionPackSection title="Recommendation">
        <p className="text-sm text-slate-700">
          <strong>{titleCase(String(h.recommendation_status ?? ""))}</strong> · {es.recommended_decision}
        </p>
        <p className="mt-1 text-sm text-slate-600">{es.rationale}</p>
        {Array.isArray(es.conditions_before_launch) && es.conditions_before_launch.length > 0 && (
          <>
            <div className="label mt-2">Conditions before launch</div>
            <ul className="list-inside list-disc text-sm text-slate-600">
              {es.conditions_before_launch.map((c: string, i: number) => <li key={i}>{c}</li>)}
            </ul>
          </>
        )}
      </DecisionPackSection>

      <DecisionPackSection title="Scorecard">
        <div className="grid gap-2 sm:grid-cols-4">
          <MetricCard label="Overall" value={`${sc.overall_score ?? "·"}`} />
          <MetricCard label="Trial potential" value={`${sc.trial_potential_score ?? "·"}`} />
          <MetricCard label="Repeat potential" value={`${sc.repeat_potential_score ?? "·"}`} />
          <MetricCard label="Risk" value={`${sc.risk_score ?? "·"}`} />
        </div>
        {sc.disclaimer && <p className="mt-2 text-xs text-slate-400">{sc.disclaimer}</p>}
      </DecisionPackSection>

      <DecisionPackSection title="Top Findings" pageBreak>
        <ul className="space-y-2 text-sm">
          {(pack.top_findings ?? []).map((f: any, i: number) => (
            <li key={i}>
              <span className="font-medium text-slate-800">{f.finding_title}</span> · {f.explanation}
              {f.supporting_metric && <span className="text-slate-500"> ({f.supporting_metric})</span>}
            </li>
          ))}
        </ul>
      </DecisionPackSection>

      <DecisionPackSection title="Biggest Risks">
        <ul className="space-y-2 text-sm">
          {(pack.biggest_risks ?? []).map((r: any, i: number) => (
            <li key={i}>
              <span className="font-medium text-rose-700">{r.risk_title}</span>{" "}
              <span className="text-xs text-slate-400">({r.severity})</span> · {r.why_it_matters}
              {r.mitigation && <span className="block text-xs text-slate-500">Mitigation: {r.mitigation}</span>}
            </li>
          ))}
        </ul>
      </DecisionPackSection>

      <DecisionPackSection title="Next Best Actions">
        <ul className="space-y-1 text-sm">
          {(pack.next_best_actions ?? []).map((a: any, i: number) => (
            <li key={i}>
              <span className="chip border-slate-200 bg-slate-50 text-slate-600">{a.priority}</span> {a.action}
              {a.owner_team && <span className="text-xs text-slate-400"> · {a.owner_team}</span>}
            </li>
          ))}
        </ul>
      </DecisionPackSection>

      <DecisionPackSection title="Scenario & Sensitivity Snapshot" pageBreak>
        <p className="text-sm text-slate-700">{pack.scenario_summary?.count ?? 0} scenario(s) saved.</p>
        <ul className="mt-1 space-y-1 text-sm">
          {(pack.scenario_summary?.scenarios ?? []).map((s: any, i: number) => (
            <li key={i}>
              <span className="font-medium text-slate-800">{s.scenario_name}</span>
              {s.delta_summary && <span className="text-slate-600"> · {s.delta_summary}</span>}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-400">{pack.sensitivity_summary?.note}</p>
      </DecisionPackSection>

      <DecisionPackSection title="Assumptions & Limitations">
        <p className="text-sm text-slate-700">
          Assumptions · high: {pack.assumptions_summary?.high_impact_count ?? 0}, medium:{" "}
          {pack.assumptions_summary?.medium_impact_count ?? 0}, low: {pack.assumptions_summary?.low_impact_count ?? 0}.
        </p>
        <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
          {(pack.assumptions_summary?.top_assumptions ?? []).map((a: any, i: number) => (
            <li key={i}>({a.impact}) {a.assumption}</li>
          ))}
        </ul>
        <div className="label mt-2">Limitations</div>
        <ul className="list-inside list-disc text-xs text-slate-500">
          {(pack.limitations ?? []).map((l: string, i: number) => <li key={i}>{l}</li>)}
        </ul>
      </DecisionPackSection>

      <DecisionPackSection title="Evidence Pack">
        {(pack.evidence_pack ?? []).map((block: any, i: number) => (
          <div key={i} className="mb-2">
            <div className="label">{block.category}</div>
            <ul className="list-inside list-disc text-xs text-slate-600">
              {(block.items ?? []).slice(0, 6).map((it: string, j: number) => <li key={j}>{it}</li>)}
            </ul>
          </div>
        ))}
      </DecisionPackSection>

      {(pack.decision_history ?? []).length > 0 && (
        <DecisionPackSection title="Decision History">
          <ul className="space-y-1 text-sm">
            {pack.decision_history.map((d: any, i: number) => (
              <li key={i} className="flex items-center justify-between border-b border-slate-100 py-1">
                <span className="text-slate-700">{d.title}</span>
                <span className="text-xs text-slate-400">{d.entry_type}</span>
              </li>
            ))}
          </ul>
        </DecisionPackSection>
      )}

      <p className="text-center text-[11px] text-slate-400">
        Simulation output is exploratory decision support, not a validated market forecast.
      </p>
    </div>
  );
}
