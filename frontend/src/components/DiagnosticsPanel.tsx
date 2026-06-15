import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDiagnostics, getReadyz, getRecentErrors, getSystemStatus } from "../api/system";
import type { AppLogEntry, Diagnostics, ReadyZ, SystemStatus } from "../types/api";
import LoadingState from "./LoadingState";

export default function DiagnosticsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [ready, setReady] = useState<ReadyZ | null>(null);
  const [diag, setDiag] = useState<Diagnostics | null>(null);
  const [errors, setErrors] = useState<AppLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setOffline(false);
    try {
      const [s, r, d, e] = await Promise.allSettled([
        getSystemStatus(),
        getReadyz(),
        getDiagnostics(),
        getRecentErrors(),
      ]);
      setStatus(s.status === "fulfilled" ? s.value : null);
      setReady(r.status === "fulfilled" ? r.value : null);
      setDiag(d.status === "fulfilled" ? d.value : null);
      setErrors(e.status === "fulfilled" ? e.value.items : []);
      if (s.status !== "fulfilled" && d.status !== "fulfilled") setOffline(true);
    } finally {
      setLoading(false);
    }
  }, []);

  const copyRequestId = useCallback(async (id: string) => {
    try {
      await navigator.clipboard?.writeText(id);
      setCopied(id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard unavailable — ignore */
    }
  }, []);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const rows: [string, string][] = [
    ["Backend", offline ? "offline" : "connected"],
    ["Readiness", ready ? ready.status : "—"],
    ["Version", status?.version ?? "—"],
    ["Environment", status?.environment ?? "—"],
    ["Demo mode", status ? String(status.demo_mode) : "—"],
    ["LLM", status ? (status.llm_configured ? "configured" : "deterministic fallback") : "—"],
    ["Database", status?.database_type ?? status?.database ?? "—"],
    ["Live streaming", status?.live_streaming_supported ? "supported" : "—"],
    ["Projects", diag ? String(diag.database.project_count) : "—"],
    ["Baseline events", diag ? String(diag.database.event_count) : "—"],
    ["Live runs", diag ? String(diag.database.live_run_count) : "—"],
    ["App log entries", diag?.database.app_log_count != null ? String(diag.database.app_log_count) : "—"],
    ["Last request ID", diag?.request_id ?? "—"],
  ];

  function downloadSnapshot() {
    const snapshot = { status, ready, diag, recent_errors: errors, captured_at: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "diagnostics_snapshot.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Diagnostics">
      <button className="flex-1 bg-slate-900/40" aria-label="Close diagnostics" onClick={onClose} />
      <aside className="h-full w-full max-w-sm overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Diagnostics</h2>
          <button className="btn-secondary" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {loading ? (
          <LoadingState label="Checking backend…" />
        ) : (
          <table className="w-full text-left text-sm">
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k} className="border-b border-slate-100">
                  <td className="py-1 pr-2 text-slate-500">{k}</td>
                  <td className="py-1 font-medium text-slate-800">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between">
            <div className="label">Recent Errors</div>
            <button className="btn-secondary text-xs" onClick={refresh} disabled={loading}>
              Refresh logs
            </button>
          </div>
          {errors.length === 0 ? (
            <p className="text-xs text-slate-400">No recent errors</p>
          ) : (
            <ul className="space-y-2">
              {errors.map((e) => (
                <li key={e.id} className="rounded border border-slate-100 bg-slate-50 p-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className={e.level === "error" ? "font-semibold text-rose-700" : "font-semibold text-amber-700"}>
                      {e.level} · {e.event_type}
                    </span>
                    {e.status_code != null && <span className="text-slate-400">{e.status_code}</span>}
                  </div>
                  <div className="mt-0.5 text-slate-700">{e.message}</div>
                  {e.request_id && (
                    <button
                      className="mt-1 text-[11px] text-slate-500 underline"
                      onClick={() => copyRequestId(e.request_id as string)}
                      title="Copy request ID"
                    >
                      {copied === e.request_id ? "Copied!" : `Copy ID: ${e.request_id.slice(0, 8)}…`}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        {diag?.warnings && diag.warnings.length > 0 && (
          <div className="mt-3">
            <div className="label">Warnings</div>
            <ul className="list-inside list-disc text-xs text-amber-700">
              {diag.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={refresh} disabled={loading}>Retry status check</button>
          <button className="btn-secondary" onClick={downloadSnapshot}>Download diagnostics snapshot</button>
          <Link className="btn-secondary" to="/data-tools" onClick={onClose}>Data Tools</Link>
        </div>
        <p className="mt-3 text-[11px] text-slate-400">Read-only operational info — no secrets exposed.</p>
      </aside>
    </div>
  );
}
