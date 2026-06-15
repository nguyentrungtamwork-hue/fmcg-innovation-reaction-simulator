interface Props {
  playing: boolean;
  speed: number; // 0.5 | 1 | 2 | 0 (instant)
  index: number;
  total: number;
  onToggle: () => void;
  onReset: () => void;
  onSpeed: (s: number) => void;
}

const SPEEDS: { label: string; value: number }[] = [
  { label: "0.5x", value: 0.5 },
  { label: "1x", value: 1 },
  { label: "2x", value: 2 },
  { label: "Instant", value: 0 },
];

export default function PlaybackControls({ playing, speed, index, total, onToggle, onReset, onSpeed }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3" aria-label="Playback controls">
      <button className="btn-primary" onClick={onToggle} disabled={total === 0}>
        {playing ? "Pause" : index >= total && total > 0 ? "Replay" : "Play"}
      </button>
      <button className="btn-secondary" onClick={onReset} disabled={total === 0}>
        Reset
      </button>
      <div className="flex items-center gap-1" role="group" aria-label="Playback speed">
        {SPEEDS.map((s) => (
          <button
            key={s.label}
            onClick={() => onSpeed(s.value)}
            className={`rounded-md px-2 py-1 text-xs font-medium ${speed === s.value ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600 hover:bg-slate-100"}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="ml-auto text-xs text-slate-500">
        {Math.min(index, total)} / {total} events
      </div>
    </div>
  );
}
