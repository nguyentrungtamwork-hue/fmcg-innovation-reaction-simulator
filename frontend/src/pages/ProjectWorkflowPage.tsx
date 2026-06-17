import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getProject } from "../api/projects";
import { analyzeOntology, getOntology, submitBrief } from "../api/ontology";
import { generateAgents, getAgentsSummary } from "../api/agents";
import { getEventsSummary, runSimulation } from "../api/simulation";
import { generateReport, getReportSummary } from "../api/reports";
import { askQuestion } from "../api/qa";
import { runScenario } from "../api/scenarios";
import type {
  AgentSummaryOut,
  EventsSummaryOut,
  OntologyOut,
  ProjectEnvelope,
  QuestionOut,
  ReportSummaryOut,
} from "../types/api";
import Stepper, { Step } from "../components/Stepper";
import StatusBadge from "../components/StatusBadge";
import MetricCard from "../components/MetricCard";
import EvidenceChip from "../components/EvidenceChip";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { SAMPLE_BRIEF, SAMPLE_BRIEF_TEXT } from "../utils/sampleBrief";
import { num, pct, titleCase } from "../utils/formatters";

const PRESET_QUESTIONS = [
  "Why is repeat purchase low?",
  "Which segment should we target first?",
  "Which claim is riskiest?",
  "What should we change before launch?",
];

export default function ProjectWorkflowPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();

  const [envelope, setEnvelope] = useState<ProjectEnvelope | null>(null);
  const [active, setActive] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  // step data
  const [briefText, setBriefText] = useState("");
  const [ontology, setOntology] = useState<OntologyOut | null>(null);
  const [agents, setAgents] = useState<AgentSummaryOut | null>(null);
  const [sim, setSim] = useState<EventsSummaryOut | null>(null);
  const [reportSummary, setReportSummary] = useState<ReportSummaryOut | null>(null);
  const [qa, setQa] = useState<QuestionOut | null>(null);

  async function refreshEnvelope() {
    try {
      setEnvelope(await getProject(projectId));
    } catch (e) {
      setError(e);
    }
  }

  useEffect(() => {
    void refreshEnvelope();
    // best-effort hydration of any already-completed steps
    void (async () => {
      try {
        setOntology(await getOntology(projectId));
      } catch {
        /* none yet */
      }
      try {
        setAgents(await getAgentsSummary(projectId));
      } catch {
        /* none yet */
      }
      try {
        const s = await getEventsSummary(projectId);
        if (s.total_events > 0) setSim(s);
      } catch {
        /* none yet */
      }
      try {
        setReportSummary(await getReportSummary(projectId));
      } catch {
        /* none yet */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function run<T>(key: string, fn: () => Promise<T>, after?: (r: T) => void) {
    setBusy(key);
    setError(null);
    try {
      const r = await fn();
      after?.(r);
      await refreshEnvelope();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  }

  const e = envelope;
  const steps: Step[] = [
    { id: 1, title: "Create Project", done: !!e },
    { id: 2, title: "Submit Brief", done: !!e?.has_brief },
    { id: 3, title: "Analyze Ontology", done: !!e?.has_ontology },
    { id: 4, title: "Generate Agents", done: (e?.agents_count ?? 0) > 0 },
    { id: 5, title: "Run Simulation", done: (e?.events_count ?? 0) > 0 },
    { id: 6, title: "Generate Report", done: !!e?.has_report },
    { id: 7, title: "Ask Questions", done: !!qa },
    { id: 8, title: "Scenario Testing", done: false },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{e?.project.name ?? "Project workflow"}</h1>
          <p className="text-sm text-slate-500">Run each step in order. Status is read back from the backend.</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge ready={!!e?.has_brief} label="Brief" />
          <StatusBadge ready={!!e?.has_ontology} label="Ontology" />
          <StatusBadge ready={(e?.agents_count ?? 0) > 0} label="Agents" />
          <StatusBadge ready={(e?.events_count ?? 0) > 0} label="Simulation" />
          <StatusBadge ready={!!e?.has_report} label="Report" />
        </div>
      </div>

      <Stepper steps={steps} active={active} onSelect={setActive} />

      {error ? <ErrorState error={error} /> : null}

      {/* STEP 1 */}
      {active === 1 && (
        <div className="card">
          <h2 className="mb-2 font-semibold text-slate-900">Step 1 · Project created</h2>
          <p className="text-sm text-slate-600">
            Project ID: <span className="font-mono text-xs">{projectId}</span>
          </p>
          <button className="btn-primary mt-3" onClick={() => setActive(2)}>
            Continue to brief →
          </button>
        </div>
      )}

      {/* STEP 2 */}
      {active === 2 && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Step 2 · Submit innovation brief</h2>
            <button className="btn-secondary" onClick={() => setBriefText(SAMPLE_BRIEF_TEXT)}>
              Load sample brief
            </button>
          </div>
          <textarea
            className="input h-56 font-mono text-xs"
            placeholder="Paste the innovation brief here, or load the FreshPlus sample…"
            value={briefText}
            onChange={(ev) => setBriefText(ev.target.value)}
          />
          <div className="flex gap-2">
            <button
              className="btn-primary"
              disabled={busy === "brief" || !briefText.trim()}
              onClick={() =>
                run(
                  "brief",
                  () =>
                    submitBrief(projectId, {
                      // when the sample text is used, also send the structured fields
                      ...(briefText === SAMPLE_BRIEF_TEXT ? SAMPLE_BRIEF : { raw_text: briefText }),
                    }),
                  () => setActive(3)
                )
              }
            >
              {busy === "brief" ? "Submitting…" : "Submit brief"}
            </button>
            {e?.has_brief && <span className="self-center text-sm text-emerald-600">Brief stored ✓</span>}
          </div>
        </div>
      )}

      {/* STEP 3 */}
      {active === 3 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 3 · Analyze ontology</h2>
          <button
            className="btn-primary"
            disabled={busy === "analyze"}
            onClick={() => run("analyze", () => analyzeOntology(projectId), setOntology)}
          >
            {busy === "analyze" ? "Analyzing…" : ontology ? "Re-analyze brief" : "Analyze brief"}
          </button>
          {busy === "analyze" && <LoadingState label="Extracting FMCG ontology…" />}
          {ontology && (
            <div className="grid gap-3 md:grid-cols-2">
              <ListBlock title="Entities" items={ontology.entities.map((x) => `${titleCase(x.type)}: ${x.name}`)} />
              <ListBlock title="Relationships" items={ontology.relationships.map((r) => `${r.from} ·${r.type}→ ${r.to}`)} />
              <ListBlock title="Purchase triggers" items={ontology.purchase_triggers} tone="emerald" />
              <ListBlock title="Adoption barriers" items={ontology.adoption_barriers} tone="red" />
              <ListBlock title="Risk signals" items={ontology.risk_signals} tone="amber" />
              <ListBlock title="Missing information" items={ontology.missing_information} tone="slate" />
            </div>
          )}
          {ontology && (
            <button className="btn-secondary" onClick={() => setActive(4)}>
              Continue to agents →
            </button>
          )}
        </div>
      )}

      {/* STEP 4 */}
      {active === 4 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 4 · Generate agents</h2>
          <button
            className="btn-primary"
            disabled={busy === "agents"}
            onClick={() =>
              run("agents", async () => {
                await generateAgents(projectId);
                return getAgentsSummary(projectId);
              }, setAgents)
            }
          >
            {busy === "agents" ? "Generating…" : agents ? "Regenerate agents" : "Generate agents"}
          </button>
          {agents && (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard label="Total agents" value={String(agents.total_agents)} />
                <MetricCard label="Consumer agents" value={String(agents.consumer_agents)} />
                <MetricCard label="Market actors" value={String(agents.market_actor_agents)} />
              </div>
              <div>
                <div className="label">Segment distribution</div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(agents.segment_distribution).map(([seg, n]) => (
                    <span key={seg} className="chip border-slate-200 bg-slate-50 text-slate-600">
                      {seg} · {n}
                    </span>
                  ))}
                </div>
              </div>
              <button className="btn-secondary" onClick={() => setActive(5)}>
                Continue to simulation →
              </button>
            </>
          )}
        </div>
      )}

      {/* STEP 5 */}
      {active === 5 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 5 · Run simulation</h2>
          <p className="text-sm text-slate-500">6 rounds · seed 42 · deterministic. Baseline run is preserved separately from scenarios.</p>
          <button
            className="btn-primary"
            disabled={busy === "sim"}
            onClick={() =>
              run("sim", async () => {
                await runSimulation(projectId, { rounds: 6, seed: 42, deterministic: true });
                return getEventsSummary(projectId);
              }, setSim)
            }
          >
            {busy === "sim" ? "Simulating…" : sim ? "Re-run simulation" : "Run simulation"}
          </button>
          {busy === "sim" && <LoadingState label="Simulating 6 launch rounds…" />}
          {sim && (
            <>
              <div className="grid gap-3 sm:grid-cols-4">
                <MetricCard label="Total events" value={String(sim.total_events)} />
                <MetricCard label="Consumer events" value={String(sim.consumer_events)} />
                <MetricCard label="Market events" value={String(sim.market_actor_events)} />
                <MetricCard label="Rounds" value={String(sim.rounds_run)} />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <TopList title="Top purchase triggers" items={sim.top_triggers} tone="emerald" />
                <TopList title="Top adoption barriers" items={sim.top_barriers} tone="red" />
              </div>
              <ActionDistribution dist={sim.action_distribution} />
              <div className="flex flex-wrap gap-2">
                <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/events`}>
                  Open event explorer →
                </Link>
                <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/studio`}>
                  Open Agent Studio →
                </Link>
                <button className="btn-secondary" onClick={() => setActive(6)}>
                  Continue to report →
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* STEP 6 */}
      {active === 6 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 6 · Generate strategic report</h2>
          <button
            className="btn-primary"
            disabled={busy === "report"}
            onClick={() =>
              run("report", async () => {
                await generateReport(projectId);
                return getReportSummary(projectId);
              }, setReportSummary)
            }
          >
            {busy === "report" ? "Generating…" : reportSummary ? "Regenerate report" : "Generate report"}
          </button>
          {busy === "report" && <LoadingState label="Synthesizing the 16-section report…" />}
          {reportSummary && (
            <div className="space-y-3">
              <div className="grid gap-3 md:grid-cols-3">
                <InfoCard label="Overall reaction" value={reportSummary.overall_market_reaction} />
                <InfoCard label="Top opportunity" value={reportSummary.top_opportunity} />
                <InfoCard label="Top risk" value={reportSummary.top_risk} />
              </div>
              <div>
                <div className="label">Key recommendations</div>
                <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                  {reportSummary.key_recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
              <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/report`}>
                Open full report →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* STEP 7 */}
      {active === 7 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 7 · Ask questions</h2>
          <div className="flex flex-wrap gap-2">
            {PRESET_QUESTIONS.map((q) => (
              <button
                key={q}
                className="btn-secondary"
                disabled={busy === "qa"}
                onClick={() => run("qa", () => askQuestion(projectId, { question: q, include_evidence: true, max_evidence_events: 4 }), setQa)}
              >
                {q}
              </button>
            ))}
          </div>
          {busy === "qa" && <LoadingState label="Answering from persisted evidence…" />}
          {qa && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">{titleCase(qa.intent)}</div>
              <p className="mt-1 text-sm text-slate-800">{qa.answer.direct_answer}</p>
              <p className="mt-2 text-xs text-slate-500">Confidence {pct(qa.answer.confidence_score)}</p>
              {qa.answer.supporting_events.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {qa.answer.supporting_events.map((ev) => (
                    <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />
                  ))}
                </div>
              )}
              <Link className="btn-secondary mt-3 inline-flex" to={`/projects/${projectId}/qa`}>
                Open Q&amp;A console →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* STEP 8 */}
      {active === 8 && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Step 8 · Scenario testing</h2>
          <p className="text-sm text-slate-500">
            Re-simulate under what-if assumptions. The baseline simulation and report are never modified.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn-primary"
              disabled={busy === "scenario"}
              onClick={() =>
                run(
                  "scenario",
                  () =>
                    runScenario(projectId, {
                      scenario_name: "10% price reduction",
                      description: "Quick test: cut shelf price by 10%.",
                      overrides: { price_change_pct: -10 },
                    }),
                  () => navigate(`/projects/${projectId}/scenarios`)
                )
              }
            >
              {busy === "scenario" ? "Running…" : "Run 10% price reduction scenario"}
            </button>
            <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/scenarios`}>
              Open Scenario Lab →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

// --- small presentational helpers ------------------------------------------

function ListBlock({ title, items, tone = "slate" }: { title: string; items: string[]; tone?: string }) {
  const toneMap: Record<string, string> = {
    emerald: "border-emerald-200 bg-emerald-50",
    red: "border-red-200 bg-red-50",
    amber: "border-amber-200 bg-amber-50",
    slate: "border-slate-200 bg-slate-50",
  };
  return (
    <div className={`rounded-lg border p-3 ${toneMap[tone]}`}>
      <div className="label">{title}</div>
      {items.length === 0 ? (
        <div className="text-xs text-slate-400">None</div>
      ) : (
        <ul className="space-y-1 text-xs text-slate-700">
          {items.slice(0, 12).map((it, i) => (
            <li key={i}>• {it}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TopList({ title, items, tone }: { title: string; items: [string, number][]; tone: string }) {
  const color = tone === "emerald" ? "text-emerald-700" : "text-red-700";
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="label">{title}</div>
      <ul className="space-y-1 text-sm">
        {items.slice(0, 5).map(([name, n], i) => (
          <li key={i} className="flex justify-between">
            <span className="text-slate-700">{name}</span>
            <span className={`font-medium ${color}`}>×{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ActionDistribution({ dist }: { dist: Record<string, number> }) {
  const entries = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <div className="label">Action distribution</div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([action, n]) => (
          <span key={action} className="chip border-slate-200 bg-slate-50 text-slate-600">
            {titleCase(action)} · {n}
          </span>
        ))}
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="label">{label}</div>
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}
