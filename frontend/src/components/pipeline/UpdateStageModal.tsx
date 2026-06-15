import { useEffect, useState } from "react";
import { PIPELINE_STAGES, STAGE_LABELS, updatePipelineStatus, type PipelineStatus } from "../../api/pipeline";

interface Props {
  open: boolean;
  projectId: string;
  current?: PipelineStatus | null;
  onClose: () => void;
  onSaved: (s: PipelineStatus) => void;
}

export default function UpdateStageModal({ open, projectId, current, onClose, onSaved }: Props) {
  const [stage, setStage] = useState<string>(current?.pipeline_stage ?? "new_concept");
  const [note, setNote] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedTag, setSavedTag] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setStage(current?.pipeline_stage ?? "new_concept");
      setNote("");
      setError(null);
      setSavedTag(null);
    }
  }, [open, current]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const result = await updatePipelineStatus(projectId, { pipeline_stage: stage, note: note || undefined, source: "manual" });
      setSavedTag(`Saved. A decision-history entry was created.`);
      onSaved(result);
    } catch (e: any) {
      setError(e?.message ?? "Failed to update stage.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Update pipeline stage">
      <button className="absolute inset-0 bg-slate-900/40" aria-label="Close" onClick={onClose} />
      <div className="card relative z-10 w-full max-w-md">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Update pipeline stage</h2>
          <button className="btn-secondary" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <label className="label" htmlFor="stage-select">New stage</label>
        <select id="stage-select" className="input mb-2" value={stage} onChange={(e) => setStage(e.target.value)}>
          {PIPELINE_STAGES.map((s) => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
        </select>
        <label className="label" htmlFor="stage-note">Note (optional)</label>
        <textarea id="stage-note" className="input h-24 w-full" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why is the stage changing?" />
        {error && <p className="mt-2 text-xs text-rose-700">{error}</p>}
        {savedTag && <p className="mt-2 text-xs text-emerald-700">{savedTag}</p>}
        <div className="mt-3 flex justify-end gap-2">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save stage"}</button>
        </div>
      </div>
    </div>
  );
}
