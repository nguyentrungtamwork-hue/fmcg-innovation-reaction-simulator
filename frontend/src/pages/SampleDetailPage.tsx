import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getSample, loadSample, type SampleDetail } from "../api/samples";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

export default function SampleDetailPage() {
  const { sampleId = "" } = useParams();
  const navigate = useNavigate();
  const [sample, setSample] = useState<SampleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLoading(true);
    getSample(sampleId).then(setSample).catch(setError).finally(() => setLoading(false));
  }, [sampleId]);

  async function load(runPipeline: boolean) {
    setBusy(true);
    setError(null);
    try {
      const res = await loadSample(sampleId, { run_pipeline: runPipeline });
      navigate(`/projects/${res.project_id}/home`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Loading sample…" />;
  if (error && !sample) return <ErrorState error={error} />;
  if (!sample) return null;

  return (
    <div className="space-y-4">
      <Link className="text-sm text-brand-700 underline" to="/samples">← Back to Sample Library</Link>
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{sample.name}</h1>
        <p className="text-sm text-slate-500">{sample.category} · {sample.target_consumer}</p>
      </div>
      {error != null && <ErrorState error={error} />}
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={busy} onClick={() => load(false)}>Load as new project</button>
        <button className="btn-secondary" disabled={busy} onClick={() => load(true)}>Load and run pipeline</button>
      </div>
      <div className="card">
        <div className="label">Recommended demo path</div>
        <p className="text-sm text-slate-700">{sample.recommended_demo_path.join(" → ") || "workflow"}</p>
        <div className="label mt-3">What to observe</div>
        <p className="text-sm text-slate-700">{sample.what_to_observe}</p>
      </div>
      <div className="card">
        <div className="label">Sample brief</div>
        <pre className="whitespace-pre-wrap text-sm text-slate-700">{sample.sample_brief_text}</pre>
      </div>
    </div>
  );
}
