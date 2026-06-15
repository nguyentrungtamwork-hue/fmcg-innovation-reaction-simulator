import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getSamples, loadSample, type SampleLoadResult, type SampleSummary } from "../api/samples";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import DemoControlPanel from "../components/DemoControlPanel";

export default function SampleLibraryPage() {
  const navigate = useNavigate();
  const [samples, setSamples] = useState<SampleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [result, setResult] = useState<SampleLoadResult | null>(null);

  useEffect(() => {
    getSamples().then((r) => setSamples(r.samples)).catch(setError).finally(() => setLoading(false));
  }, []);

  const categories = useMemo(() => Array.from(new Set(samples.map((s) => s.category))).sort(), [samples]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return samples.filter((s) => {
      if (category && s.category !== category) return false;
      if (!q) return true;
      return [s.name, s.short_description, s.key_claim, s.target_consumer, s.category]
        .join(" ").toLowerCase().includes(q);
    });
  }, [samples, category, query]);

  async function handleLoad(sampleId: string, runPipeline: boolean) {
    setLoadingId(sampleId + (runPipeline ? ":run" : ""));
    setError(null);
    setResult(null);
    try {
      const res = await loadSample(sampleId, { run_pipeline: runPipeline });
      setResult(res);
      try { localStorage.setItem("last_sample_loaded", sampleId); } catch { /* ignore */ }
    } catch (e) {
      setError(e);
    } finally {
      setLoadingId(null);
    }
  }

  if (loading) return <LoadingState label="Loading sample library…" />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Sample Library</h1>
        <p className="text-sm text-slate-500">
          Ready-made (fictional) FMCG innovation concepts. Load one as a new project to explore the
          full workflow. These are illustrative concepts — not real products or market validation.
        </p>
      </div>

      {error != null && <ErrorState error={error} />}

      <DemoControlPanel />

      {result && (
        <div className="card border-emerald-200 bg-emerald-50" role="status">
          <div className="font-medium text-emerald-800">Sample loaded as a new project.</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button className="btn-primary" onClick={() => navigate(`/projects/${result.project_id}/home`)}>Open Project Home</button>
            <Link className="btn-secondary" to={`/projects/${result.project_id}/workflow`}>Open Workflow</Link>
            <Link className="btn-secondary" to={`/projects/${result.project_id}/studio`}>Open Agent Studio</Link>
          </div>
          {result.warnings.length > 0 && <ul className="mt-2 text-xs text-amber-700">{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="sample-search" className="sr-only">Search samples</label>
        <input
          id="sample-search"
          className="input max-w-xs py-1 text-sm"
          placeholder="Search samples…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label htmlFor="sample-category" className="text-sm text-slate-500">Category</label>
        <select id="sample-category" className="input max-w-xs py-1 text-sm" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-slate-500">No samples match your search.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2" data-tour="samples-grid">
          {filtered.map((s) => (
            <article key={s.sample_id} className="card flex flex-col gap-2">
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-900">{s.name}</h2>
                <span className="chip border-slate-200 bg-slate-50 text-slate-500">{s.category}</span>
              </div>
              <p className="text-sm text-slate-600">{s.short_description}</p>
              <dl className="text-xs text-slate-500">
                <div><dt className="inline font-medium">Target: </dt><dd className="inline">{s.target_consumer}</dd></div>
                <div><dt className="inline font-medium">Key claim: </dt><dd className="inline">{s.key_claim}</dd></div>
                <div><dt className="inline font-medium">What to observe: </dt><dd className="inline">{s.what_to_observe}</dd></div>
              </dl>
              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <Link className="btn-secondary" to={`/samples/${s.sample_id}`}>View sample brief</Link>
                <button className="btn-primary" disabled={loadingId != null} onClick={() => handleLoad(s.sample_id, false)}>
                  {loadingId === s.sample_id ? "Loading…" : "Load as new project"}
                </button>
                <button className="btn-secondary" disabled={loadingId != null} onClick={() => handleLoad(s.sample_id, true)}>
                  {loadingId === s.sample_id + ":run" ? "Running…" : "Load and run pipeline"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
