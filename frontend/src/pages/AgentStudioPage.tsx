import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getStudioState } from "../api/studio";
import { getOverview } from "../api/overview";
import { runSimulation } from "../api/simulation";
import { getProject } from "../api/projects";
import { analyzeOntology } from "../api/ontology";
import { generateAgents } from "../api/agents";
import type { OverviewOut, ProjectEnvelope, StudioEvent, StudioState } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import AgentDrawer from "../components/AgentDrawer";
import PlaybackControls from "../components/studio/PlaybackControls";
import RoundTimeline from "../components/studio/RoundTimeline";
import LiveEventStream from "../components/studio/LiveEventStream";
import LivePanel from "../components/studio/LivePanel";
import StudioGraphPanel from "../components/studio/StudioGraphPanel";
import StudioProcessPanel from "../components/studio/StudioProcessPanel";
import StudioConsole, { type ConsoleLine } from "../components/studio/StudioConsole";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";
import { useTour } from "../tours/TourProvider";
import { num, titleCase } from "../utils/formatters";

type Engine = "replay" | "live";
type Layout = "graph" | "split" | "workbench";

const TRIAL = new Set(["purchase_trial"]);
const REPEAT = new Set(["repeat_purchase_intent", "repeat_purchase"]);
const RECOMMEND = new Set(["recommend", "share_with_friend"]);
const COMPLAINT = new Set(["complain", "comment_negative"]);

const SPEED_MS: Record<string, number> = { "0.5": 700, "1": 350, "2": 160 };

interface Filters {
  round: number | "all";
  segment: string;
  agentType: string;
  action: string;
  trigger: string;
  barrier: string;
  sentiment: string;
}

const EMPTY: Filters = { round: "all", segment: "", agentType: "", action: "", trigger: "", barrier: "", sentiment: "" };

function fmtTime(d = new Date()): string {
  const p = (n: number, l = 2) => String(n).padStart(l, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}
let _seq = 0;
function logLine(text: string, kind: ConsoleLine["kind"] = "info"): ConsoleLine {
  return { id: `l${Date.now()}_${_seq++}`, time: fmtTime(), text, kind };
}

export default function AgentStudioPage() {
  const { projectId = "" } = useParams();
  const reducedMotion = usePrefersReducedMotion();
  const { startTour } = useTour();
  const [state, setState] = useState<StudioState | null>(null);
  const [overview, setOverview] = useState<OverviewOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [inspect, setInspect] = useState<string | null>(null);
  const [envelope, setEnvelope] = useState<ProjectEnvelope | null>(null);
  const [stepBusy, setStepBusy] = useState<string | null>(null);

  const [engine, setEngine] = useState<Engine>("replay");
  const [layout, setLayout] = useState<Layout>("split");
  const [showEdgeLabels, setShowEdgeLabels] = useState(false);
  const [sysLines, setSysLines] = useState<ConsoleLine[]>([]);

  const initialized = useRef(false);
  const timer = useRef<number | null>(null);
  const lastLogged = useRef(0);

  function pushSys(...lines: ConsoleLine[]) {
    setSysLines((prev) => [...prev, ...lines].slice(-120));
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      try {
        setEnvelope(await getProject(projectId));
      } catch {
        /* ignore */
      }
      try {
        setOverview(await getOverview(projectId));
      } catch {
        /* ignore */
      }
      const s = await getStudioState(projectId);
      setState(s);
      pushSys(
        logLine(`Loading studio data: ${projectId.slice(0, 12)}`),
        logLine(`Project loaded: ${s.project.status}`, "success"),
        logLine(`Graph data loaded: ${s.graph.nodes.length} nodes, ${s.graph.edges.length} edges`),
        logLine(`Simulation events available: ${s.events.length}`),
      );
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const events = state?.events ?? [];

  useEffect(() => {
    if (state && !initialized.current) {
      initialized.current = true;
      if (state.events.length === 0 && state.graph.nodes.length > 0) setEngine("live");
    }
  }, [state]);

  const opts = useMemo(() => {
    const u = (key: keyof StudioEvent) => [...new Set(events.map((e) => e[key]).filter(Boolean) as string[])].sort();
    return { segments: u("segment_name"), actions: u("action_type"), triggers: u("trigger_detected"), barriers: u("barrier_detected") };
  }, [events]);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (filters.round !== "all" && e.round_number !== filters.round) return false;
      if (filters.segment && e.segment_name !== filters.segment) return false;
      if (filters.agentType && e.agent_type !== filters.agentType) return false;
      if (filters.action && e.action_type !== filters.action) return false;
      if (filters.trigger && e.trigger_detected !== filters.trigger) return false;
      if (filters.barrier && e.barrier_detected !== filters.barrier) return false;
      if (filters.sentiment) {
        const s = e.sentiment_score ?? 0;
        if (filters.sentiment === "positive" && !(s > 0.15)) return false;
        if (filters.sentiment === "negative" && !(s < -0.05)) return false;
        if (filters.sentiment === "neutral" && !(s >= -0.05 && s <= 0.15)) return false;
      }
      return true;
    });
  }, [events, filters]);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
    lastLogged.current = 0;
  }, [filtered.length]);

  useEffect(() => {
    if (timer.current) { window.clearInterval(timer.current); timer.current = null; }
    if (playing && speed > 0) {
      timer.current = window.setInterval(() => {
        setIndex((prev) => (prev < filtered.length ? prev + 1 : prev));
      }, SPEED_MS[String(speed)] ?? 350);
    }
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, [playing, speed, filtered.length]);

  useEffect(() => {
    if (index >= filtered.length && playing) setPlaying(false);
  }, [index, filtered.length, playing]);

  const revealed = filtered.slice(0, index);
  const current = index > 0 ? filtered[index - 1] : null;
  const filtersActive = JSON.stringify(filters) !== JSON.stringify(EMPTY);
  const highlightAgentIds = useMemo(
    () => (filtersActive ? new Set(filtered.map((e) => e.agent_id)) : new Set<string>()),
    [filtersActive, filtered]
  );

  // feed newly revealed events into the console
  useEffect(() => {
    if (index > lastLogged.current) {
      const newOnes = filtered.slice(lastLogged.current, index);
      const lines = newOnes.map((e) =>
        logLine(
          `R${e.round_number} · ${e.segment_name ?? titleCase(e.agent_type)} → ${titleCase(e.action_type)} (sentiment ${num(e.sentiment_score, 2)})`,
          (e.sentiment_score ?? 0) < -0.05 ? "warn" : "event"
        )
      );
      if (lines.length) pushSys(...lines);
      lastLogged.current = index;
    } else if (index === 0) {
      lastLogged.current = 0;
    }
  }, [index, filtered]);

  const counters = useMemo(() => {
    const c = { trial: 0, repeat: 0, recommend: 0, complaint: 0, sent: 0, n: 0 };
    for (const e of revealed) {
      if (TRIAL.has(e.action_type)) c.trial++;
      if (REPEAT.has(e.action_type)) c.repeat++;
      if (RECOMMEND.has(e.action_type)) c.recommend++;
      if (COMPLAINT.has(e.action_type)) c.complaint++;
      if (e.sentiment_score !== null && e.agent_type === "consumer") { c.sent += e.sentiment_score; c.n++; }
    }
    return c;
  }, [revealed]);

  function toggle() {
    if (index >= filtered.length) setIndex(0);
    if (speed === 0) { setIndex(filtered.length); setPlaying(false); return; }
    setPlaying((p) => !p);
  }
  function reset() { setPlaying(false); setIndex(0); }

  async function runSim() {
    setRunning(true);
    setError(null);
    pushSys(logLine("POST /api/v1/projects/{id}/simulate — running simulation…", "warn"));
    try {
      await runSimulation(projectId, { rounds: 6, seed: 42, deterministic: true });
      pushSys(logLine("✓ Simulation completed", "success"));
      await load();
    } catch (e) {
      setError(e);
      pushSys(logLine("✗ Simulation failed", "warn"));
    } finally {
      setRunning(false);
    }
  }

  async function runStep(key: string, label: string, fn: () => Promise<unknown>) {
    setStepBusy(key);
    setError(null);
    pushSys(logLine(`${label} — processing…`, "warn"));
    try {
      await fn();
      pushSys(logLine(`✓ ${label} complete`, "success"));
      await load();
    } catch (e) {
      setError(e);
      pushSys(logLine(`✗ ${label} failed`, "warn"));
    } finally {
      setStepBusy(null);
    }
  }

  function stepRound(delta: number) {
    setFilters((f) => {
      const cur = f.round === "all" ? (delta > 0 ? 0 : 7) : f.round;
      const next = Math.max(1, Math.min(6, cur + delta));
      return { ...f, round: next };
    });
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.key === " ") { e.preventDefault(); toggle(); }
      else if (e.key.toLowerCase() === "r") reset();
      else if (e.key === "ArrowRight") stepRound(1);
      else if (e.key === "ArrowLeft") stepRound(-1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, playing, speed, filtered.length]);

  if (loading) return <LoadingState label="Loading studio…" />;

  const hasGraph = !!state && state.graph.nodes.length > 0;
  const pipeline = overview?.pipeline_status ?? {
    has_brief: !!envelope?.has_brief,
    has_ontology: !!envelope?.has_ontology,
    has_agents: (envelope?.agents_count ?? 0) > 0,
    has_simulation: events.length > 0,
    has_report: !!envelope?.has_report,
    has_briefing: false,
  };

  const graphPanel = state ? (
    <StudioGraphPanel
      graph={state.graph}
      activeAgentId={current?.agent_id ?? null}
      highlightAgentIds={highlightAgentIds}
      onSelect={setInspect}
      reducedMotion={reducedMotion}
      showEdgeLabels={showEdgeLabels}
      onToggleEdgeLabels={setShowEdgeLabels}
      onRefresh={() => void load()}
      expanded={layout === "graph"}
      onToggleExpand={() => setLayout((l) => (l === "graph" ? "split" : "graph"))}
      live={playing || (engine === "live")}
    />
  ) : null;

  const processPanel = (
    <StudioProcessPanel
      projectId={projectId}
      pipeline={pipeline}
      agentsCount={state?.agents.length ?? envelope?.agents_count ?? 0}
      eventsCount={events.length}
      busyStep={stepBusy}
      running={running}
      onAnalyze={() => runStep("ont", "Ontology Extraction", () => analyzeOntology(projectId))}
      onAgents={() => runStep("agents", "Agent Generation", () => generateAgents(projectId))}
      onRunSim={runSim}
    />
  );

  return (
    <div className="space-y-4" data-tour="studio-root">
      {/* Top bar */}
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-slate-900">Agent Studio</h1>
            <span className={`chip ${events.length > 0 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${events.length > 0 ? "bg-emerald-500" : "bg-slate-400"}`} /> {events.length > 0 ? "Ready" : "No simulation yet"}
            </span>
          </div>
          <p className="text-sm text-slate-500">Watch FMCG consumer agents & market actors react — {state?.project.name}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="chip border-slate-200 bg-slate-50 text-slate-600">Agents: {state?.agents.length ?? 0}</span>
            <span className="chip border-slate-200 bg-slate-50 text-slate-600">Events: {events.length}</span>
            <span className="chip border-slate-200 bg-slate-50 text-slate-600">
              Mode: {playing ? "Playing" : index >= filtered.length && filtered.length > 0 ? "Done" : "Idle"}
            </span>
          </div>
        </div>

        {/* step + live status (MiroFish-style) */}
        <StepStatus pipeline={pipeline} running={running} playing={playing} live={engine === "live"} />

        {/* layout tabs */}
        <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-1" role="tablist" aria-label="Studio layout">
          {(["graph", "split", "workbench"] as Layout[]).map((l) => (
            <button
              key={l}
              role="tab"
              aria-selected={layout === l}
              onClick={() => setLayout(l)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition ${layout === l ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
            >
              {l}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {events.length > 0 && <button className="btn-secondary" onClick={() => { reset(); setPlaying(true); }}>▶ Replay</button>}
          <Link className="btn-secondary" to={`/projects/${projectId}/report`}>Report</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/briefing`}>Briefing</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/events`}>Events</Link>
          <button className="btn-secondary" onClick={() => startTour("studio", projectId)}>Tour</button>
        </div>
      </div>

      {error ? <ErrorState error={error} /> : null}

      {/* engine toggle */}
      {hasGraph && (
        <div className="flex items-center gap-1" role="tablist" aria-label="Studio engine" data-tour="studio-live">
          {(["replay", "live"] as Engine[]).map((md) => (
            <button
              key={md}
              role="tab"
              aria-selected={engine === md}
              onClick={() => setEngine(md)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${engine === md ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600 hover:bg-slate-100"}`}
            >
              {md === "replay" ? "Replay Mode" : "Live Mode"}
            </button>
          ))}
          <span className="ml-2 text-xs text-slate-400">
            {engine === "live" ? "Stream a new simulation as it generates." : "Animate the saved simulation events."}
          </span>
        </div>
      )}

      {engine === "live" && state ? (
        <>
          <LivePanel
            projectId={projectId}
            graph={state.graph}
            onCompleted={() => { setEngine("replay"); reset(); pushSys(logLine("✓ Live run completed — switched to Replay", "success")); void load(); }}
            onInspect={setInspect}
          />
          <StudioConsole lines={sysLines} projectId={projectId} />
        </>
      ) : events.length === 0 ? (
        <div className="card space-y-3">
          <h2 className="font-semibold text-slate-900">Get this simulation ready</h2>
          <p className="text-sm text-slate-600">Run the remaining pipeline steps, then watch the playback here. This is a quick path — the full Workflow page still works.</p>
          <ol className="space-y-2">
            <GuidedStep n={1} label="Submit a brief" done={!!pipeline.has_brief}
              action={!pipeline.has_brief ? <Link className="btn-secondary" to={`/projects/${projectId}/workflow`}>Open Workflow →</Link> : null} />
            <GuidedStep n={2} label="Analyze ontology" done={!!pipeline.has_ontology}
              action={pipeline.has_brief && !pipeline.has_ontology ? <button className="btn-secondary" disabled={stepBusy === "ont"} onClick={() => runStep("ont", "Ontology Extraction", () => analyzeOntology(projectId))}>{stepBusy === "ont" ? "Analyzing…" : "Analyze"}</button> : null} />
            <GuidedStep n={3} label="Generate agents" done={!!pipeline.has_agents}
              action={pipeline.has_ontology && !pipeline.has_agents ? <button className="btn-secondary" disabled={stepBusy === "agents"} onClick={() => runStep("agents", "Agent Generation", () => generateAgents(projectId))}>{stepBusy === "agents" ? "Generating…" : "Generate agents"}</button> : null} />
            <GuidedStep n={4} label="Run simulation" done={false}
              action={pipeline.has_agents ? <button className="btn-primary" disabled={running} onClick={runSim}>{running ? "Simulating…" : "Run simulation"}</button> : null} />
          </ol>
          <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/workflow`}>← Back to workflow</Link>
        </div>
      ) : (
        <>
          {/* GRAPH layout: graph fills, process panel below as a strip is omitted */}
          {layout === "graph" && (
            <div className="space-y-4">
              {graphPanel}
              <StudioConsole lines={sysLines} projectId={projectId} />
            </div>
          )}

          {/* SPLIT layout: graph + process panel, console below */}
          {layout === "split" && (
            <>
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">{graphPanel}</div>
                <div className="lg:col-span-1">{processPanel}</div>
              </div>
              <StudioConsole lines={sysLines} projectId={projectId} />
            </>
          )}

          {/* WORKBENCH layout: full power-user controls */}
          {layout === "workbench" && (
            <>
              <div className="grid gap-3 sm:grid-cols-5">
                <MetricCard label="Trials" value={String(counters.trial)} tone="up" />
                <MetricCard label="Repeats" value={String(counters.repeat)} tone="up" />
                <MetricCard label="Recommends" value={String(counters.recommend)} tone="up" />
                <MetricCard label="Complaints" value={String(counters.complaint)} tone="down" />
                <MetricCard label="Avg sentiment" value={counters.n ? num(counters.sent / counters.n, 2) : "—"} />
              </div>

              <div className="card space-y-3">
                <PlaybackControls playing={playing} speed={speed} index={index} total={filtered.length} onToggle={toggle} onReset={reset} onSpeed={setSpeed} />
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] text-slate-400">Keys: Space play/pause · R reset · ←/→ round</span>
                  <span className="ml-auto text-[11px] text-slate-400">View:</span>
                  {([["", "All"], ["consumer", "Consumers only"], ["market_actor", "Market actors only"]] as [string, string][]).map(([v, label]) => (
                    <button key={label} onClick={() => setFilters((f) => ({ ...f, agentType: v }))}
                      className={`rounded-md px-2 py-1 text-xs font-medium ${filters.agentType === v ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600 hover:bg-slate-100"}`}>
                      {label}
                    </button>
                  ))}
                </div>
                <RoundTimeline rounds={state!.rounds} currentRound={current?.round_number ?? null} selectedRound={filters.round} onSelect={(r) => setFilters((f) => ({ ...f, round: r }))} />
                <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6" aria-label="Studio filters">
                  <Select label="Segment" value={filters.segment} onChange={(v) => setFilters((f) => ({ ...f, segment: v }))} options={opts.segments} />
                  <Select label="Agent type" value={filters.agentType} onChange={(v) => setFilters((f) => ({ ...f, agentType: v }))} options={["consumer", "market_actor"]} />
                  <Select label="Action" value={filters.action} onChange={(v) => setFilters((f) => ({ ...f, action: v }))} options={opts.actions} />
                  <Select label="Trigger" value={filters.trigger} onChange={(v) => setFilters((f) => ({ ...f, trigger: v }))} options={opts.triggers} />
                  <Select label="Barrier" value={filters.barrier} onChange={(v) => setFilters((f) => ({ ...f, barrier: v }))} options={opts.barriers} />
                  <Select label="Sentiment" value={filters.sentiment} onChange={(v) => setFilters((f) => ({ ...f, sentiment: v }))} options={["positive", "neutral", "negative"]} />
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">{graphPanel}</div>
                <div className="card">
                  <h2 className="mb-2 font-semibold text-slate-900">Live event stream</h2>
                  <div className="max-h-[460px] overflow-y-auto">
                    <LiveEventStream projectId={projectId} events={[...revealed].reverse().slice(0, 40)} onInspect={setInspect} />
                  </div>
                </div>
              </div>

              <StudioConsole lines={sysLines} projectId={projectId} />
            </>
          )}
        </>
      )}

      <AgentDrawer projectId={projectId} agentId={inspect} onClose={() => setInspect(null)} />
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div>
      <label className="label">{label}</label>
      <select className="input py-1 text-sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>{titleCase(o)}</option>
        ))}
      </select>
    </div>
  );
}

const PIPELINE_STEPS: { key: keyof PipelineStatus; label: string }[] = [
  { key: "has_brief", label: "Brief" },
  { key: "has_ontology", label: "Ontology" },
  { key: "has_agents", label: "Agents" },
  { key: "has_simulation", label: "Simulation" },
  { key: "has_report", label: "Report" },
  { key: "has_briefing", label: "Briefing" },
];

type PipelineStatus = {
  has_brief: boolean;
  has_ontology: boolean;
  has_agents: boolean;
  has_simulation: boolean;
  has_report: boolean;
  has_briefing: boolean;
};

function StepStatus({ pipeline, running, playing, live }: { pipeline: PipelineStatus; running: boolean; playing: boolean; live: boolean }) {
  const total = PIPELINE_STEPS.length;
  const firstIncomplete = PIPELINE_STEPS.findIndex((s) => !pipeline[s.key]);
  const idx = firstIncomplete === -1 ? total - 1 : firstIncomplete;
  const stepNo = idx + 1;
  const stepLabel = firstIncomplete === -1 ? "Complete" : PIPELINE_STEPS[idx].label;

  // status dot: never render the bare word "Ready" (reserved for the title chip)
  const status = running
    ? { label: "Simulating", dot: "bg-amber-500", pulse: true }
    : live
    ? { label: "Live stream", dot: "bg-emerald-500", pulse: true }
    : playing
    ? { label: "Replaying", dot: "bg-brand-600", pulse: true }
    : firstIncomplete === -1
    ? { label: "Standby", dot: "bg-emerald-500", pulse: false }
    : { label: "Standby", dot: "bg-slate-400", pulse: false };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-1.5" aria-label="Studio status">
      <div className="flex items-baseline gap-1.5 text-sm">
        <span className="font-mono text-xs uppercase tracking-wide text-slate-400">Step</span>
        <span className="font-semibold text-slate-900">{stepNo}/{total}</span>
        <span className="font-medium text-slate-600">· {stepLabel}</span>
      </div>
      <span className="flex items-center gap-1.5 border-l border-slate-200 pl-3 text-xs font-medium text-slate-600">
        <span className={`h-2 w-2 rounded-full ${status.dot} ${status.pulse ? "studio-pulse" : ""}`} />
        {status.label}
      </span>
    </div>
  );
}

function GuidedStep({ n, label, done, action }: { n: number; label: string; done: boolean; action: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3 rounded-lg border border-slate-200 p-2">
      <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${done ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-600"}`}>
        {done ? "✓" : n}
      </span>
      <span className="flex-1 text-sm text-slate-700">{label}</span>
      {action}
    </li>
  );
}
