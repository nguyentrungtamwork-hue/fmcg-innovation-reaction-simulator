import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createProject, getProjects } from "../api/projects";
import { ApiError } from "../api/client";
import type { Project } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import OnboardingPanel from "../components/OnboardingPanel";
import DemoControlPanel from "../components/DemoControlPanel";
import { shortDate } from "../utils/formatters";

export default function ProjectListPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [market, setMarket] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    setError(null);
    try {
      setProjects(await getProjects());
    } catch (e) {
      setError(e);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const p = await createProject({
        name: name.trim(),
        category: category.trim() || null,
        market: market.trim() || null,
      });
      navigate(`/projects/${p.id}/workflow`);
    } catch (err) {
      setError(err);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      {projects !== null && projects.length === 0 && <OnboardingPanel />}
      {projects !== null && projects.length === 0 && <DemoControlPanel />}
      <div className="grid gap-6 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Projects</h1>
        <p className="mb-4 text-sm text-slate-500">
          Each project runs the full pipeline: brief → ontology → agents → simulation → report → Q&amp;A → scenarios.
        </p>
        {error instanceof ApiError && error.code === "network_error" && (
          <div className="mb-4">
            <ErrorState error={error} />
          </div>
        )}
        {projects && projects.some((p) => p.name.startsWith("FreshPlus Demo")) && (
          <button
            className="btn-secondary mb-3"
            onClick={() => {
              const demo = projects.find((p) => p.name.startsWith("FreshPlus Demo"));
              if (demo) navigate(`/projects/${demo.id}/studio`);
            }}
          >
            ▶ Open demo in Agent Studio
          </button>
        )}
        {projects === null ? (
          <LoadingState label="Loading projects…" />
        ) : projects.length === 0 ? (
          <div className="card space-y-3 text-sm text-slate-500">
            <p>No projects yet · pick a way to start:</p>
            <div className="flex flex-wrap gap-2">
              <Link className="btn-primary" to="/samples">Load a sample concept</Link>
              <Link className="btn-secondary" to="/data-tools">Import a project bundle</Link>
            </div>
            <p className="text-xs text-slate-400">
              Or create a blank project on the right, or run <code className="rounded bg-slate-100 px-1">python scripts/seed_demo.py</code> for a FreshPlus demo.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => navigate(`/projects/${p.id}/workflow`)}
                className="card flex w-full items-center justify-between text-left hover:border-brand-300"
              >
                <div>
                  <div className="font-medium text-slate-900">{p.name}</div>
                  <div className="text-xs text-slate-500">
                    {[p.category, p.market].filter(Boolean).join(" · ") || "No category/market"} · created {shortDate(p.created_at)}
                  </div>
                </div>
                <span className="chip border-slate-200 bg-slate-50 text-slate-500">{p.status}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">New project</h2>
          <form onSubmit={onCreate} className="space-y-3">
            <div>
              <label className="label">Project name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="FreshPlus Herbal Cool launch" />
            </div>
            <div>
              <label className="label">Category (optional)</label>
              <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Ready-to-drink tea" />
            </div>
            <div>
              <label className="label">Market (optional)</label>
              <input className="input" value={market} onChange={(e) => setMarket(e.target.value)} placeholder="Vietnam" />
            </div>
            <button className="btn-primary w-full" disabled={creating || !name.trim()}>
              {creating ? "Creating…" : "Create project"}
            </button>
            {error && !(error instanceof ApiError && error.code === "network_error") ? <ErrorState error={error} /> : null}
          </form>
        </div>
      </section>
      </div>
    </div>
  );
}
