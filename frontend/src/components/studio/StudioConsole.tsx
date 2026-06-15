import { useEffect, useRef } from "react";

export interface ConsoleLine {
  id: string;
  time: string;
  text: string;
  kind?: "info" | "event" | "success" | "warn";
}

const KIND_COLOR: Record<NonNullable<ConsoleLine["kind"]>, string> = {
  info: "text-slate-200",
  event: "text-sky-300",
  success: "text-emerald-300",
  warn: "text-amber-300",
};

export default function StudioConsole({
  lines,
  projectId,
  heightClass = "max-h-56",
}: {
  lines: ConsoleLine[];
  projectId: string;
  heightClass?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length]);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-sm" data-tour="studio-stream">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
        <span className="flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 studio-pulse" aria-hidden="true" />
          System Dashboard
        </span>
        <span className="flex items-center gap-3 font-mono text-[11px] text-slate-500">
          <span>{lines.length} lines</span>
          <span>proj_{projectId.replace(/-/g, "").slice(0, 12)}</span>
        </span>
      </div>
      <div ref={ref} className={`${heightClass} overflow-y-auto px-4 py-3 font-mono text-xs leading-relaxed`} aria-label="System console" aria-live="polite">
        {lines.length === 0 ? (
          <div className="text-slate-500">Waiting for activity…</div>
        ) : (
          lines.map((l) => (
            <div key={l.id} className="flex gap-3">
              <span className="shrink-0 text-slate-500">{l.time}</span>
              <span className={KIND_COLOR[l.kind ?? "info"]}>{l.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
