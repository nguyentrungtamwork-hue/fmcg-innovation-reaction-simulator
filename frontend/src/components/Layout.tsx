import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { getSystemStatus } from "../api/system";
import { getProjects } from "../api/projects";
import type { Project, SystemStatus } from "../types/api";
import GlossaryModal from "./GlossaryModal";
import DiagnosticsPanel from "./DiagnosticsPanel";
import DemoControlPanel from "./DemoControlPanel";
import ErrorBoundary from "./ErrorBoundary";

const SURFACES: [string, string][] = [
  ["Home", "home"], ["Workflow", "workflow"], ["Studio", "studio"], ["Events", "events"],
  ["Report", "report"], ["Briefing", "briefing"], ["Scenario", "scenarios"],
  ["Sensitivity", "sensitivity"], ["Decisions", "decisions"],
];

const navBase =
  "px-3 py-2 rounded-lg text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600";

function navClass({ isActive }: { isActive: boolean }) {
  return `${navBase} ${isActive ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"}`;
}

export default function Layout() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const p = projectId ? `/projects/${projectId}` : null;

  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [offline, setOffline] = useState(false);
  const [checking, setChecking] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [jumpProject, setJumpProject] = useState("");
  const [jumpSurface, setJumpSurface] = useState("home");
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const [diagOpen, setDiagOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);

  useEffect(() => {
    getProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  function jump() {
    const pid = jumpProject || projectId;
    if (pid) navigate(`/projects/${pid}/${jumpSurface}`);
  }

  const check = useCallback(async () => {
    setChecking(true);
    try {
      setStatus(await getSystemStatus());
      setOffline(false);
    } catch {
      setStatus(null);
      setOffline(true);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  return (
    <div className="min-h-full">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[60] focus:rounded focus:bg-brand-600 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>
      {offline && (
        <div className="flex items-center justify-center gap-3 bg-red-600 px-4 py-2 text-sm text-white print:hidden" role="alert">
          <span>Backend is not reachable. Start FastAPI on port 8000 or run <code className="rounded bg-red-700 px-1">docker compose up</code>.</span>
          <button onClick={check} disabled={checking} className="rounded bg-white/20 px-2 py-0.5 font-medium hover:bg-white/30 disabled:opacity-50">
            {checking ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}

      <header className="border-b border-slate-200 bg-white print:hidden">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              FM
            </span>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-slate-900">FMCG Innovation Reaction Simulator</div>
              <div className="text-xs text-slate-500">Internal launch decision-support dashboard</div>
            </div>
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Primary">
            <NavLink to="/" end className={navClass} data-tour="nav-projects">
              Projects
            </NavLink>
            <NavLink to="/portfolio" className={navClass}>
              Portfolio
            </NavLink>
            <NavLink to="/compare" className={navClass}>
              Compare
            </NavLink>
            <NavLink to="/portfolio/decision-board" className={navClass}>
              Board
            </NavLink>
            <NavLink to="/portfolio/pipeline" className={navClass}>
              Pipeline
            </NavLink>
            <NavLink to="/portfolio/activity" className={navClass}>
              Activity
            </NavLink>
            <NavLink to="/samples" className={navClass} data-tour="nav-samples">
              Samples
            </NavLink>
            <NavLink to="/data-tools" className={navClass}>
              Data Tools
            </NavLink>
            {p && (
              <>
                <NavLink to={`${p}/home`} className={navClass}>
                  Home
                </NavLink>
                <NavLink to={`${p}/workflow`} className={navClass}>
                  Workflow
                </NavLink>
                <NavLink to={`${p}/events`} className={navClass}>
                  Events
                </NavLink>
                <NavLink to={`${p}/studio`} className={navClass}>
                  Studio
                </NavLink>
                <NavLink to={`${p}/report`} className={navClass}>
                  Report
                </NavLink>
                <NavLink to={`${p}/briefing`} className={navClass}>
                  Briefing
                </NavLink>
                <NavLink to={`${p}/qa`} className={navClass}>
                  Q&amp;A
                </NavLink>
                <NavLink to={`${p}/scenarios`} className={navClass}>
                  Scenario Lab
                </NavLink>
                <NavLink to={`${p}/sensitivity`} className={navClass}>
                  Sensitivity
                </NavLink>
                <NavLink to={`${p}/decisions`} className={navClass}>
                  History
                </NavLink>
              </>
            )}
          </nav>
        </div>
        {/* global jump */}
        <div className="border-t border-slate-100 bg-slate-50 print:hidden">
          <form
            className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-4 py-2 text-xs"
            aria-label="Global jump"
            onSubmit={(e) => { e.preventDefault(); jump(); }}
          >
            <span className="font-medium text-slate-500">Jump to</span>
            <select className="input max-w-[16rem] py-1 text-xs" aria-label="Project" value={jumpProject} onChange={(e) => setJumpProject(e.target.value)}>
              <option value="">{projectId ? "Current project" : "Select project…"}</option>
              {projects.map((pr) => <option key={pr.id} value={pr.id}>{pr.name}</option>)}
            </select>
            <select className="input max-w-[10rem] py-1 text-xs" aria-label="Surface" value={jumpSurface} onChange={(e) => setJumpSurface(e.target.value)}>
              {SURFACES.map(([label, s]) => <option key={s} value={s}>{label}</option>)}
            </select>
            <button className="btn-secondary py-1" disabled={!jumpProject && !projectId}>Go</button>
          </form>
        </div>
      </header>

      <main id="main-content" role="main" tabIndex={-1} className="mx-auto max-w-7xl px-4 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <footer className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-2 px-4 py-6 text-center text-xs text-slate-400 print:hidden">
        <StatusPill ok={!offline} label={offline ? "Backend offline" : "Backend connected"} />
        {status && (
          <>
            <StatusPill ok={status.llm_configured} label={status.llm_configured ? "LLM configured" : "Deterministic fallback"} neutral={!status.llm_configured} />
            {status.demo_mode && <span className="chip border-amber-200 bg-amber-50 text-amber-700">Demo Mode</span>}
            <span className="chip border-slate-200 bg-slate-50 text-slate-500">v{status.version}</span>
          </>
        )}
        <button className="underline hover:text-slate-600" onClick={() => setGlossaryOpen(true)}>Glossary</button>
        <button className="underline hover:text-slate-600" onClick={() => setDiagOpen(true)}>Diagnostics</button>
        <button className="underline hover:text-slate-600" onClick={() => setDemoOpen((v) => !v)} aria-expanded={demoOpen}>Tours &amp; Demo</button>
        {demoOpen && (
          <div className="w-full pt-2">
            <DemoControlPanel />
          </div>
        )}
        <span className="w-full pt-2">
          Exploratory decision support — simulated reactions, not a guaranteed market forecast. Validate with real research.
        </span>
      </footer>

      <GlossaryModal open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
      <DiagnosticsPanel open={diagOpen} onClose={() => setDiagOpen(false)} />
    </div>
  );
}

function StatusPill({ ok, label, neutral }: { ok: boolean; label: string; neutral?: boolean }) {
  const cls = neutral
    ? "border-slate-200 bg-slate-50 text-slate-500"
    : ok
    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
    : "border-red-200 bg-red-50 text-red-700";
  return (
    <span className={`chip ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${neutral ? "bg-slate-400" : ok ? "bg-emerald-500" : "bg-red-500"}`} />
      {label}
    </span>
  );
}
