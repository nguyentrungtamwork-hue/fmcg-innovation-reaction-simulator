import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTour } from "../tours/TourProvider";
import { loadSample } from "../api/samples";
import { TOUR_DISCLAIMER } from "../tours/tours";

const DEMO_SAMPLE = "ready_to_drink_tea";

export default function DemoControlPanel({ compact = false }: { compact?: boolean }) {
  const { startTour, resetTourState } = useTour();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function playDemo(full: boolean) {
    setBusy(full ? "full" : "quick");
    setError(null);
    try {
      const res = await loadSample(DEMO_SAMPLE, { run_pipeline: full });
      try { localStorage.setItem("demo_autoplay_seen", "true"); } catch { /* ignore */ }
      startTour("first_time", res.project_id);
      navigate(`/projects/${res.project_id}/home`);
    } catch {
      setError("Could not load the demo sample. Is the backend running?");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className={compact ? "" : "card"} aria-label="Demo & tours">
      {!compact && <h2 className="mb-2 text-base font-semibold text-slate-800">Demo &amp; guided tours</h2>}
      <div className="flex flex-wrap gap-2">
        <button className="btn-secondary" onClick={() => startTour("first_time")}>Start First-Time Tour</button>
        <button className="btn-secondary" onClick={() => startTour("studio")}>Start Agent Studio Tour</button>
        <button className="btn-primary" disabled={busy != null} onClick={() => playDemo(false)}>
          {busy === "quick" ? "Loading…" : "Play Demo (Quick)"}
        </button>
        <button className="btn-secondary" disabled={busy != null} onClick={() => playDemo(true)} title="Loads a sample and runs the full deterministic pipeline — may take a little time.">
          {busy === "full" ? "Running…" : "Play Demo (Full)"}
        </button>
        <button className="btn-secondary" onClick={resetTourState}>Reset onboarding/tour state</button>
        <Link className="btn-secondary" to="/samples">Open Sample Library</Link>
      </div>
      {error && <p className="mt-2 text-xs text-rose-700">{error}</p>}
      <p className="mt-2 text-[11px] text-slate-400">
        <strong>Quick</strong> loads a sample so you can run steps yourself. <strong>Full</strong> also runs the
        deterministic pipeline (may take a little time). {TOUR_DISCLAIMER}
      </p>
    </section>
  );
}
