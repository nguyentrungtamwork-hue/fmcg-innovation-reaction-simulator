import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createDecision, deleteDecision, getTimeline, listDecisions } from "../api/history";
import { listSnapshots } from "../api/portfolio";
import type { DecisionOut, SnapshotListItem, TimelineItem } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { shortDate, titleCase } from "../utils/formatters";

const ENTRY_TYPES = ["note", "decision", "change", "meeting", "validation_result"];

const ICON: Record<string, string> = {
  project_created: "🟢",
  brief_submitted: "📄",
  ontology_generated: "🧩",
  agents_generated: "👥",
  simulation_run: "▶️",
  report_generated: "📊",
  scenario_created: "🧪",
  snapshot_created: "📌",
};

export default function DecisionHistoryPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [decisions, setDecisions] = useState<DecisionOut[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotListItem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [entryType, setEntryType] = useState("decision");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState("");
  const [relatedSnapshot, setRelatedSnapshot] = useState("");

  async function refresh() {
    const [t, d] = await Promise.all([getTimeline(projectId), listDecisions(projectId)]);
    setTimeline(t.timeline);
    setDecisions(d);
  }

  useEffect(() => {
    Promise.all([refresh(), listSnapshots(projectId).then(setSnapshots)])
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createDecision(projectId, {
        entry_type: entryType,
        title: title.trim(),
        body: body.trim(),
        related_snapshot_id: relatedSnapshot || null,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setTitle("");
      setBody("");
      setTags("");
      setRelatedSnapshot("");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: string) {
    await deleteDecision(projectId, id);
    await refresh();
  }

  if (loading) return <LoadingState label="Loading decision history…" />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Decision history</h1>
          <p className="text-sm text-slate-500">Project timeline + your decisions and notes. Read-only milestones are merged in.</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to={`/projects/${projectId}/decision-pack`}>Decision Pack</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/briefing`}>Briefing</Link>
          <Link className="btn-secondary" to={`/projects/${projectId}/report`}>← Report</Link>
        </div>
      </div>

      {error ? <ErrorState error={error} /> : null}

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="card">
            <h2 className="mb-3 font-semibold text-slate-900">Timeline</h2>
            <ol className="space-y-3">
              {timeline.map((t, i) => {
                const isDecision = t.type.startsWith("decision:");
                const icon = isDecision ? "📝" : ICON[t.type] ?? "•";
                return (
                  <li key={i} className="flex gap-3">
                    <span className="text-lg leading-none">{icon}</span>
                    <div className="flex-1 border-b border-slate-100 pb-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-800">{t.title}</span>
                        <span className="text-xs text-slate-400">{shortDate(t.timestamp)}</span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {isDecision ? titleCase(t.type.split(":")[1]) : titleCase(t.type)}
                        {t.description ? ` — ${t.description}` : ""}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </section>

        <section className="space-y-4">
          <div className="card">
            <h2 className="mb-3 font-semibold text-slate-900">Add entry</h2>
            <form onSubmit={onAdd} className="space-y-2">
              <div>
                <label className="label" htmlFor="etype">Type</label>
                <select id="etype" className="input py-1" value={entryType} onChange={(e) => setEntryType(e.target.value)}>
                  {ENTRY_TYPES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
                </select>
              </div>
              <input className="input" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <textarea className="input h-20" placeholder="Body (optional)" value={body} onChange={(e) => setBody(e.target.value)} />
              <input className="input" placeholder="Tags (comma-separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
              {snapshots.length > 0 && (
                <select className="input py-1" aria-label="Related snapshot" value={relatedSnapshot} onChange={(e) => setRelatedSnapshot(e.target.value)}>
                  <option value="">Related snapshot (optional)</option>
                  {snapshots.map((s) => <option key={s.snapshot_id} value={s.snapshot_id}>{s.snapshot_name}</option>)}
                </select>
              )}
              <button className="btn-primary" disabled={saving || !title.trim()}>{saving ? "Saving…" : "Add entry"}</button>
            </form>
          </div>

          <div className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Your entries</h2>
            {decisions.length === 0 ? (
              <p className="text-sm text-slate-500">No decisions logged yet.</p>
            ) : (
              <ul className="space-y-2">
                {decisions.map((d) => (
                  <li key={d.id} className="rounded-lg border border-slate-200 p-2">
                    <div className="flex items-center justify-between">
                      <span className="chip border-brand-100 bg-brand-50 text-brand-700">{titleCase(d.entry_type)}</span>
                      <button className="btn-danger" onClick={() => onDelete(d.id)}>Delete</button>
                    </div>
                    <div className="mt-1 text-sm font-medium text-slate-800">{d.title}</div>
                    {d.body && <div className="text-xs text-slate-600">{d.body}</div>}
                    {d.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {d.tags.map((t) => <span key={t} className="chip border-slate-200 bg-slate-50 text-slate-500">{t}</span>)}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
