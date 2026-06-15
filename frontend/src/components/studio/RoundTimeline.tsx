import type { RoundSummary } from "../../types/api";

interface Props {
  rounds: RoundSummary[];
  currentRound: number | null;
  selectedRound: number | "all";
  onSelect: (r: number | "all") => void;
}

export default function RoundTimeline({ rounds, currentRound, selectedRound, onSelect }: Props) {
  return (
    <div className="flex flex-wrap items-stretch gap-2" aria-label="Round timeline">
      <button
        onClick={() => onSelect("all")}
        className={`rounded-lg border px-3 py-2 text-xs font-medium ${selectedRound === "all" ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
      >
        All rounds
      </button>
      {rounds.map((r) => {
        const active = currentRound === r.round_number;
        const selected = selectedRound === r.round_number;
        const total = r.consumer_events + r.market_actor_events;
        return (
          <button
            key={r.round_number}
            onClick={() => onSelect(r.round_number)}
            className={`min-w-[8rem] rounded-lg border px-3 py-2 text-left ${selected ? "border-brand-600 bg-brand-50" : active ? "border-amber-400 bg-amber-50" : "border-slate-200 bg-white"}`}
          >
            <div className="text-xs font-semibold text-slate-800">Round {r.round_number}</div>
            <div className="truncate text-[10px] text-slate-500">{r.stage_name}</div>
            <div className="text-[10px] text-slate-500">{total} events · sent {r.avg_sentiment.toFixed(2)}</div>
          </button>
        );
      })}
    </div>
  );
}
