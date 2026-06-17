import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { generateBriefing, getBriefing } from "../api/briefing";
import type { BriefingGenerateIn, BriefingOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import EvidenceChip from "../components/EvidenceChip";
import AskBriefingTab from "../components/AskBriefingTab";
import TailorTab from "../components/TailorTab";
import BoardSummaryTab from "../components/BoardSummaryTab";
import { downloadText, pct, titleCase } from "../utils/formatters";

type Tab = "briefing" | "ask" | "tailor" | "board";
const TABS: { id: Tab; label: string }[] = [
  { id: "briefing", label: "Briefing" },
  { id: "ask", label: "Ask Briefing" },
  { id: "tailor", label: "Tailor by Audience" },
  { id: "board", label: "Board Summary" },
];

const AUDIENCES = ["executive", "brand_team", "trade_sales", "rd_product", "consumer_insight"];
const TONES = ["concise", "boardroom", "working_session"];

const STATUS_TONE: Record<string, string> = {
  move_forward: "border-emerald-200 bg-emerald-50 text-emerald-800",
  validate_before_move_forward: "border-amber-200 bg-amber-50 text-amber-800",
  revise_and_retest: "border-orange-200 bg-orange-50 text-orange-800",
  hold: "border-red-200 bg-red-50 text-red-800",
};

const READY_TONE: Record<string, string> = {
  ready: "border-emerald-200 bg-emerald-50 text-emerald-700",
  caution: "border-amber-200 bg-amber-50 text-amber-700",
  not_ready: "border-red-200 bg-red-50 text-red-700",
};

export default function BriefingPage() {
  const { projectId = "" } = useParams();
  const [opts, setOpts] = useState<BriefingGenerateIn>({
    audience: "executive",
    tone: "concise",
    include_evidence: true,
    include_decision_history: true,
    include_next_actions: true,
  });
  const [briefing, setBriefing] = useState<BriefingOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showMd, setShowMd] = useState(false);
  const [tab, setTab] = useState<Tab>("briefing");

  useEffect(() => {
    getBriefing(projectId)
      .then(setBriefing)
      .catch(() => {
        /* none yet · leave empty */
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setBriefing(await generateBriefing(projectId, opts));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Loading briefing…" />;

  const p = briefing?.briefing_payload;
  const h = p?.briefing_header;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Executive launch briefing</h1>
          <p className="text-sm text-slate-500">An evidence-grounded narrative for stakeholder review. Decision support, not a forecast.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-primary" to={`/projects/${projectId}/decision-pack`}>Create stakeholder decision pack</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/report`}>← Report</Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-slate-200 print:hidden" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-t-lg px-3 py-2 text-sm font-medium ${tab === t.id ? "border-b-2 border-brand-600 text-brand-700" : "text-slate-500 hover:text-slate-700"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "ask" && <AskBriefingTab projectId={projectId} />}
      {tab === "tailor" && <TailorTab projectId={projectId} />}
      {tab === "board" && <BoardSummaryTab projectId={projectId} />}

      {tab === "briefing" && (
      <>
      <div className="card flex flex-wrap items-end gap-3 print:hidden">
        <div>
          <label className="label" htmlFor="aud">Audience</label>
          <select id="aud" className="input py-1" value={opts.audience} onChange={(e) => setOpts({ ...opts, audience: e.target.value })}>
            {AUDIENCES.map((a) => <option key={a} value={a}>{titleCase(a)}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="tone">Tone</label>
          <select id="tone" className="input py-1" value={opts.tone} onChange={(e) => setOpts({ ...opts, tone: e.target.value })}>
            {TONES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
          </select>
        </div>
        <label className="chip cursor-pointer border-slate-200 bg-white text-slate-600">
          <input type="checkbox" className="accent-brand-600" checked={!!opts.include_evidence} onChange={(e) => setOpts({ ...opts, include_evidence: e.target.checked })} />
          Evidence
        </label>
        <label className="chip cursor-pointer border-slate-200 bg-white text-slate-600">
          <input type="checkbox" className="accent-brand-600" checked={!!opts.include_decision_history} onChange={(e) => setOpts({ ...opts, include_decision_history: e.target.checked })} />
          Decision history
        </label>
        <button className="btn-primary" disabled={busy} onClick={run}>{busy ? "Generating…" : briefing ? "Regenerate briefing" : "Generate briefing"}</button>
      </div>

      {error ? <ErrorState error={error} /> : null}
      {busy && <LoadingState label="Assembling the briefing…" />}

      {p && h && !busy && (
        <div className="space-y-5">
          <div className={`rounded-lg border p-3 ${STATUS_TONE[h.recommendation_status] ?? "border-slate-200 bg-slate-50"}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-lg font-semibold">{titleCase(h.recommendation_status)}</div>
              <div className="text-sm">Overall {h.overall_score}/100 · confidence {h.confidence_label} · {briefing?.source_mode}</div>
            </div>
            <p className="mt-1 text-sm">{p.decision_recommendation.recommended_decision} · {p.decision_recommendation.rationale}</p>
          </div>

          <div className="flex flex-wrap gap-2 print:hidden">
            <button className="btn-secondary" onClick={() => downloadText(`briefing-${projectId}.md`, briefing!.markdown, "text/markdown")}>Download Markdown</button>
            <button className="btn-secondary" onClick={() => downloadText(`briefing-${projectId}.json`, JSON.stringify(p, null, 2), "application/json")}>Download JSON</button>
            <button className="btn-secondary" onClick={() => setShowMd((v) => !v)}>{showMd ? "Hide" : "Show"} markdown</button>
            <button className="btn-primary" onClick={() => window.print()}>Print briefing</button>
          </div>

          <section className="card">
            <h2 className="mb-1 font-semibold text-slate-900">Situation</h2>
            <p className="text-sm text-slate-700">{p.situation.one_paragraph_context}</p>
            <p className="mt-1 text-xs text-slate-500">{p.situation.category_or_market_context} · {p.situation.current_decision_point}</p>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Top findings</h2>
            <ul className="space-y-2 text-sm">
              {p.top_findings.map((f, i) => (
                <li key={i} className="rounded-lg border border-slate-200 p-2">
                  <div className="font-medium text-slate-800">{f.finding_title} <span className="text-xs text-slate-400">({f.supporting_metric})</span></div>
                  <div className="text-xs text-slate-600">{f.explanation} {f.business_implication}</div>
                  {f.supporting_evidence.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1 print:hidden">
                      {f.supporting_evidence.map((ev) => <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />)}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Biggest risks</h2>
            <ul className="space-y-2 text-sm">
              {p.biggest_risks.map((r, i) => (
                <li key={i} className="rounded-lg border border-red-100 bg-red-50 p-2">
                  <div className="font-medium text-red-800">{r.risk_title} <span className="text-xs">({r.severity})</span></div>
                  <div className="text-xs text-slate-600">{r.why_it_matters} <em>Mitigation:</em> {r.mitigation}</div>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Readiness</h2>
            <div className="flex flex-wrap gap-2">
              {([
                ["Trial", p.readiness_assessment.trial_readiness],
                ["Repeat", p.readiness_assessment.repeat_readiness],
                ["Claim", p.readiness_assessment.claim_readiness],
                ["Channel", p.readiness_assessment.channel_readiness],
                ["Confidence", p.readiness_assessment.confidence_readiness],
                ["Overall", p.readiness_assessment.overall_readiness],
              ] as [string, string][]).map(([label, val]) => (
                <span key={label} className={`chip ${READY_TONE[val] ?? "border-slate-200 bg-slate-50 text-slate-500"}`}>
                  {label}: {val.replace("_", " ")}
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">{p.readiness_assessment.readiness_reasoning}</p>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Next best actions</h2>
            <ul className="space-y-2 text-sm">
              {p.next_best_actions.map((a, i) => (
                <li key={i} className="rounded-lg border border-slate-200 p-2">
                  <span className="chip mr-2 border-brand-100 bg-brand-50 text-brand-700">{a.priority}</span>
                  <span className="font-medium text-slate-800">{a.action}</span>
                  <div className="mt-1 text-xs text-slate-500">Owner: {a.owner_team} · effort: {a.effort} · validate via {a.validation_method}</div>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Validation plan</h2>
            <ul className="space-y-1 text-sm">
              {p.validation_plan.map((v, i) => (
                <li key={i} className="text-slate-700">
                  <span className="chip mr-1 border-slate-200 bg-slate-50 text-slate-500">{v.priority}</span>
                  {v.question} → <span className="font-medium">{v.recommended_method}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Evidence pack</h2>
            <div className="grid gap-3 md:grid-cols-2 text-xs text-slate-600">
              <div><div className="label">Scorecard</div><ul className="list-inside list-disc">{p.evidence_pack.scorecard_evidence.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              <div><div className="label">Segments</div><ul className="list-inside list-disc">{p.evidence_pack.segment_evidence.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              <div><div className="label">Assumptions</div><ul className="list-inside list-disc">{p.evidence_pack.assumption_evidence.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              <div><div className="label">History / scenarios</div><ul className="list-inside list-disc">{[...p.evidence_pack.scenario_or_sensitivity_evidence, ...p.evidence_pack.decision_history_evidence].map((s, i) => <li key={i}>{s}</li>)}</ul></div>
            </div>
            {p.evidence_pack.event_evidence.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1 print:hidden">
                {p.evidence_pack.event_evidence.map((ev) => <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />)}
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Limitations</h2>
            <ul className="list-inside list-disc space-y-1 text-xs text-slate-500">
              {p.limitations.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </section>

          {showMd && (
            <section className="card">
              <h2 className="mb-2 font-semibold text-slate-900">Markdown</h2>
              <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{briefing!.markdown}</pre>
            </section>
          )}
        </div>
      )}

      {!briefing && !busy && (
        <div className="card text-sm text-slate-500">No briefing yet. Set audience/tone and click Generate.</div>
      )}
      </>
      )}
    </div>
  );
}
