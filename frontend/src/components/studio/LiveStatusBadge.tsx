import type { LiveStatus } from "../../hooks/useLiveSimulation";

const MAP: Record<LiveStatus, { label: string; cls: string }> = {
  idle: { label: "Idle", cls: "border-slate-200 bg-slate-50 text-slate-500" },
  starting: { label: "Starting…", cls: "border-amber-200 bg-amber-50 text-amber-700" },
  streaming: { label: "● Live", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  completed: { label: "Completed", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  failed: { label: "Failed", cls: "border-red-200 bg-red-50 text-red-700" },
  disconnected: { label: "Disconnected", cls: "border-amber-200 bg-amber-50 text-amber-700" },
};

export default function LiveStatusBadge({ status }: { status: LiveStatus }) {
  const m = MAP[status];
  return <span className={`chip ${m.cls}`} aria-label="Live status">{m.label}</span>;
}
