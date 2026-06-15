import { useState } from "react";
import type { LiveStartIn } from "../../types/api";

interface Props {
  disabled: boolean;
  onStart: (params: LiveStartIn) => void;
}

export default function LiveSimulationControls({ disabled, onStart }: Props) {
  const [rounds, setRounds] = useState(6);
  const [seed, setSeed] = useState(42);
  const [forceRerun, setForceRerun] = useState(true);
  const [delay, setDelay] = useState(120);

  return (
    <div className="card flex flex-wrap items-end gap-3" aria-label="Live simulation controls">
      <div>
        <label className="label" htmlFor="lv-rounds">Rounds</label>
        <select id="lv-rounds" className="input py-1" value={rounds} onChange={(e) => setRounds(Number(e.target.value))}>
          {[1, 2, 3, 4, 5, 6].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="lv-seed">Seed</label>
        <input id="lv-seed" type="number" className="input w-24 py-1" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
      </div>
      <div>
        <label className="label" htmlFor="lv-delay">Event delay (ms)</label>
        <input id="lv-delay" type="number" min={0} max={2000} step={20} className="input w-28 py-1" value={delay} onChange={(e) => setDelay(Number(e.target.value))} />
      </div>
      <label className="chip cursor-pointer border-slate-200 bg-white text-slate-600">
        <input type="checkbox" className="accent-brand-600" checked={forceRerun} onChange={(e) => setForceRerun(e.target.checked)} />
        Force rerun
      </label>
      <button
        className="btn-primary"
        disabled={disabled}
        onClick={() => onStart({ rounds, seed, force_rerun: forceRerun, event_delay_ms: delay, deterministic: true, include_market_actors: true })}
      >
        ▶ Start Live Simulation
      </button>
    </div>
  );
}
