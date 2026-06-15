import type { LiveProgress } from "../../types/api";

export default function LiveProgressBar({ progress }: { progress: LiveProgress | null }) {
  const pct = progress?.percent ?? 0;
  return (
    <div aria-label="Live progress">
      <div className="mb-1 flex justify-between text-xs text-slate-500">
        <span>Round {progress?.round ?? 0} / {progress?.rounds_total ?? 6}</span>
        <span>{progress?.events_emitted ?? 0} / {progress?.events_expected ?? 0} events ({pct.toFixed(0)}%)</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded bg-slate-100">
        <div className="h-full rounded bg-brand-600 transition-all" style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}
