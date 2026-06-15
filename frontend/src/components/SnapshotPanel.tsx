import { useEffect, useState } from "react";
import { createSnapshot, deleteSnapshot, getScorecard, getSnapshot, listSnapshots } from "../api/portfolio";
import type { Scorecard, SnapshotListItem, SnapshotOut } from "../types/api";
import ScorecardCard from "./ScorecardCard";
import LoadingState from "./LoadingState";
import ErrorState from "./ErrorState";
import { downloadText, shortDate } from "../utils/formatters";

export default function SnapshotPanel({ projectId }: { projectId: string }) {
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotListItem[]>([]);
  const [detail, setDetail] = useState<SnapshotOut | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setSnapshots(await listSnapshots(projectId));
  }

  useEffect(() => {
    setLoading(true);
    Promise.all([getScorecard(projectId).then(setScorecard), refresh()])
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createSnapshot(projectId, { snapshot_name: name.trim(), description: description.trim() });
      setName("");
      setDescription("");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: string) {
    await deleteSnapshot(projectId, id);
    if (detail?.snapshot_id === id) setDetail(null);
    await refresh();
  }

  if (loading) return <section className="card"><LoadingState label="Loading scorecard…" /></section>;

  return (
    <section className="space-y-4">
      <h2 className="font-semibold text-slate-900">Concept scorecard &amp; snapshots</h2>
      {error ? <ErrorState error={error} /> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {scorecard && <ScorecardCard sc={scorecard} exportable />}

        <div className="card space-y-3 print:hidden">
          <form onSubmit={onCreate} className="space-y-2">
            <div className="label mb-0">Save a named snapshot</div>
            <input className="input" placeholder="Snapshot name (e.g. Baseline Concept v1)" value={name} onChange={(e) => setName(e.target.value)} />
            <input className="input" placeholder="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
            <button className="btn-primary" disabled={saving || !name.trim()}>{saving ? "Saving…" : "Create snapshot"}</button>
          </form>

          {snapshots.length > 0 && (
            <ul className="space-y-2">
              {snapshots.map((s) => (
                <li key={s.snapshot_id} className="flex items-center justify-between rounded-lg border border-slate-200 p-2">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{s.snapshot_name}</div>
                    <div className="text-xs text-slate-500">{shortDate(s.created_at)}</div>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-secondary" onClick={() => getSnapshot(projectId, s.snapshot_id).then(setDetail)}>View</button>
                    <button className="btn-danger" onClick={() => onDelete(s.snapshot_id)}>Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {detail && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">Snapshot: {detail.snapshot_name}</h3>
            <button className="btn-secondary print:hidden" onClick={() => setDetail(null)}>Close</button>
          </div>
          {detail.description && <p className="text-sm text-slate-600">{detail.description}</p>}
          <ScorecardCard sc={detail.scorecard} exportable />
          <div className="flex gap-2 print:hidden">
            <button className="btn-secondary" onClick={() => downloadText(`snapshot-${detail.snapshot_id}.md`, detail.markdown, "text/markdown")}>
              Download snapshot Markdown
            </button>
            <button className="btn-secondary" onClick={() => downloadText(`snapshot-${detail.snapshot_id}.json`, JSON.stringify(detail.report_payload, null, 2), "application/json")}>
              Download snapshot JSON
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
