import { useState } from "react";
import { askBriefing } from "../api/briefing";
import type { BriefingAskOut } from "../types/api";
import EvidenceChip from "./EvidenceChip";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import { pct, titleCase } from "../utils/formatters";

const PRESETS = [
  "Why this recommendation?",
  "Explain this briefing for executives",
  "What should Brand do next?",
  "What should R&D validate first?",
  "What evidence supports this?",
  "What should we not overclaim?",
];

export default function AskBriefingTab({ projectId }: { projectId: string }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<BriefingAskOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function ask(q: string) {
    if (!q.trim()) return;
    setQuestion(q);
    setLoading(true);
    setError(null);
    try {
      setResult(await askBriefing(projectId, { question: q, include_evidence: true, max_evidence_items: 5 }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  const a = result?.answer;

  return (
    <div className="space-y-4">
      <div className="card space-y-3">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((q) => (
            <button key={q} className="btn-secondary" disabled={loading} onClick={() => ask(q)}>{q}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); void ask(question); }} className="flex gap-2">
          <input className="input" placeholder="Ask the briefing a follow-up question…" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <button className="btn-primary" disabled={loading || !question.trim()}>Ask</button>
        </form>
      </div>

      {loading && <LoadingState label="Answering from the briefing…" />}
      {error ? <ErrorState error={error} /> : null}

      {a && !loading && (
        <div className="card space-y-2">
          <div className="flex items-center justify-between">
            <span className="chip border-brand-100 bg-brand-50 text-brand-700">{titleCase(result!.intent)}</span>
            <span className="text-xs text-slate-500">Confidence {pct(a.confidence_score)} · {result!.source_mode}</span>
          </div>
          <p className="text-sm text-slate-800">{a.direct_answer}</p>
          <p className="text-xs text-slate-500">{a.audience_framing}</p>
          {a.supporting_evidence.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {a.supporting_evidence.map((ev) => <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />)}
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-2">
            {a.related_next_actions.length > 0 && (
              <div><div className="label">Related actions</div><ul className="list-inside list-disc text-xs text-slate-600">{a.related_next_actions.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            )}
            {a.related_risks.length > 0 && (
              <div><div className="label">Related risks</div><ul className="list-inside list-disc text-xs text-slate-600">{a.related_risks.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            )}
          </div>
          <div className="label">Limitations</div>
          <ul className="list-inside list-disc text-xs text-slate-500">{a.limitations.map((x, i) => <li key={i}>{x}</li>)}</ul>
          {a.recommended_follow_up.length > 0 && (
            <div className="flex flex-wrap gap-2 print:hidden">
              {a.recommended_follow_up.map((q) => <button key={q} className="btn-secondary" onClick={() => ask(q)}>{q}</button>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
