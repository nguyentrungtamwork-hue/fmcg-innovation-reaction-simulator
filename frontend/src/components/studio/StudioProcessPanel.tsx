import { Link } from "react-router-dom";

type StepState = "complete" | "processing" | "next" | "pending";

interface Pipeline {
  has_brief: boolean;
  has_ontology: boolean;
  has_agents: boolean;
  has_simulation: boolean;
  has_report: boolean;
  has_briefing: boolean;
}

function Badge({ state }: { state: StepState }) {
  const map: Record<StepState, [string, string]> = {
    complete: ["COMPLETE", "border-emerald-200 bg-emerald-50 text-emerald-700"],
    processing: ["PROCESSING", "border-amber-300 bg-amber-500 text-white"],
    next: ["READY TO RUN", "border-brand-300 bg-brand-50 text-brand-700"],
    pending: ["WAITING", "border-slate-200 bg-slate-100 text-slate-400"],
  };
  const [label, cls] = map[state];
  return (
    <span className={`chip text-[10px] font-semibold tracking-wide ${cls}`}>
      {state === "processing" && <span className="h-1.5 w-1.5 rounded-full bg-white studio-pulse" aria-hidden="true" />}
      {label}
    </span>
  );
}

function StepCard({
  n,
  title,
  endpoint,
  description,
  state,
  stat,
  cta,
}: {
  n: string;
  title: string;
  endpoint: string;
  description: string;
  state: StepState;
  stat?: { label: string; value: string }[];
  cta?: React.ReactNode;
}) {
  const accent =
    state === "next" ? "border-brand-300 ring-1 ring-brand-100"
    : state === "processing" ? "border-amber-300 ring-1 ring-amber-100"
    : "";
  return (
    <div className={`card ${accent}`} aria-label={`Step ${n} ${title}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold text-slate-300">{n}</span>
          <h3 className="text-base font-semibold text-slate-900">{title}</h3>
        </div>
        <Badge state={state} />
      </div>
      <div className="mt-1 font-mono text-[11px] uppercase tracking-wide text-slate-400">{endpoint}</div>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
      {stat && stat.length > 0 && (
        <div className={`mt-3 grid gap-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-center ${stat.length === 1 ? "grid-cols-1" : stat.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
          {stat.map((s) => (
            <div key={s.label}>
              <div className="text-2xl font-bold tracking-tight text-slate-900">{s.value}</div>
              <div className="mt-0.5 text-[10px] uppercase tracking-wide text-slate-400">{s.label}</div>
            </div>
          ))}
        </div>
      )}
      {cta && <div className="mt-3 flex flex-wrap gap-2">{cta}</div>}
    </div>
  );
}

export default function StudioProcessPanel({
  projectId,
  pipeline,
  agentsCount,
  eventsCount,
  busyStep,
  running,
  onAnalyze,
  onAgents,
  onRunSim,
}: {
  projectId: string;
  pipeline: Pipeline;
  agentsCount: number;
  eventsCount: number;
  busyStep: string | null;
  running: boolean;
  onAnalyze: () => void;
  onAgents: () => void;
  onRunSim: () => void;
}) {
  const p = pipeline;
  // first incomplete step = the "next" highlight
  const order: (keyof Pipeline)[] = ["has_brief", "has_ontology", "has_agents", "has_simulation", "has_report", "has_briefing"];
  const firstIncomplete = order.find((k) => !p[k]);
  const stateOf = (key: keyof Pipeline, busy: boolean): StepState =>
    busy ? "processing" : p[key] ? "complete" : key === firstIncomplete ? "next" : "pending";

  return (
    <div className="space-y-3" aria-label="Simulation process panel">
      <StepCard
        n="01"
        title="Innovation Brief"
        endpoint="POST /api/v1/projects/{id}/brief"
        description="Capture the concept, claims, target consumers and risks that seed the simulation."
        state={stateOf("has_brief", false)}
        cta={!p.has_brief ? <Link className="btn-secondary" to={`/projects/${projectId}/workflow`}>Open Workflow →</Link> : null}
      />
      <StepCard
        n="02"
        title="Ontology Extraction"
        endpoint="POST /api/v1/projects/{id}/analyze"
        description="Extract claims, segments, triggers and barriers · the structured map the agents react to."
        state={stateOf("has_ontology", busyStep === "ont")}
        cta={p.has_brief && !p.has_ontology ? <button className="btn-secondary" disabled={busyStep === "ont"} onClick={onAnalyze}>{busyStep === "ont" ? "Analyzing…" : "Analyze"}</button> : null}
      />
      <StepCard
        n="03"
        title="Agent Generation"
        endpoint="POST /api/v1/projects/{id}/agents/generate"
        description="Build simulated consumer personas + market actors grounded in the ontology."
        state={stateOf("has_agents", busyStep === "agents")}
        stat={p.has_agents ? [{ label: "Agents", value: String(agentsCount) }] : undefined}
        cta={p.has_ontology && !p.has_agents ? <button className="btn-secondary" disabled={busyStep === "agents"} onClick={onAgents}>{busyStep === "agents" ? "Generating…" : "Generate agents"}</button> : null}
      />
      <StepCard
        n="04"
        title="Reaction Simulation"
        endpoint="POST /api/v1/projects/{id}/simulate"
        description="Run the deterministic 6-round funnel; agents react and emit events you can replay."
        state={stateOf("has_simulation", running)}
        stat={p.has_simulation ? [
          { label: "Agents", value: String(agentsCount) },
          { label: "Events", value: String(eventsCount) },
          { label: "Rounds", value: "6" },
        ] : undefined}
        cta={p.has_agents && !p.has_simulation ? <button className="btn-primary" disabled={running} onClick={onRunSim}>{running ? "Simulating…" : "Run simulation"}</button> : null}
      />
      <StepCard
        n="05"
        title="Strategic Report"
        endpoint="POST /api/v1/projects/{id}/report/generate"
        description="16-section launch read grounded in the simulated evidence."
        state={stateOf("has_report", false)}
        cta={p.has_simulation ? <Link className={p.has_report ? "btn-secondary" : "btn-primary"} to={`/projects/${projectId}/report`}>{p.has_report ? "Open Report" : "Generate Report →"}</Link> : null}
      />
      <StepCard
        n="06"
        title="Executive Briefing"
        endpoint="POST /api/v1/projects/{id}/briefing/generate"
        description="Stakeholder-ready narrative with findings, risks and next best actions."
        state={stateOf("has_briefing", false)}
        cta={p.has_report ? <Link className="btn-secondary" to={`/projects/${projectId}/briefing`}>{p.has_briefing ? "Open Briefing" : "Generate Briefing →"}</Link> : null}
      />
    </div>
  );
}
