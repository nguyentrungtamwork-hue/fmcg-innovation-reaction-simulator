import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { askQuestion } from "../api/qa";
import type { QuestionOut } from "../types/api";
import EvidenceChip from "../components/EvidenceChip";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import { pct, titleCase } from "../utils/formatters";

const PRESETS = [
  "Why is repeat purchase low?",
  "Which segment should we target first?",
  "Which claim created the most skepticism?",
  "What is the biggest adoption barrier?",
  "Which channel performed best?",
  "Interview 3 skeptical consumers.",
];

export default function QAConsolePage() {
  const { projectId = "" } = useParams();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QuestionOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function ask(q: string) {
    if (!q.trim()) return;
    setQuestion(q);
    setLoading(true);
    setError(null);
    try {
      setResult(await askQuestion(projectId, { question: q, include_evidence: true, max_evidence_events: 5 }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  const a = result?.answer;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Q&amp;A console</h1>
        <p className="text-sm text-slate-500">
          Answers are grounded strictly in this project's persisted simulation, report, and agent memory.
        </p>
      </div>

      <div className="card space-y-3">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((q) => (
            <button key={q} className="btn-secondary" disabled={loading} onClick={() => ask(q)}>
              {q}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void ask(question);
          }}
          className="flex gap-2"
        >
          <input
            className="input"
            placeholder="Ask about repeat, segments, claims, pricing, channels, barriers…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button className="btn-primary" disabled={loading || !question.trim()}>
            Ask
          </button>
        </form>
      </div>

      {loading && <LoadingState label="Answering from persisted evidence…" />}
      {error ? <ErrorState error={error} /> : null}

      {a && !loading && (
        <div className="space-y-4">
          <div className="card space-y-2">
            <div className="flex items-center justify-between">
              <span className="chip border-brand-100 bg-brand-50 text-brand-700">{titleCase(result!.intent)}</span>
              <span className="text-xs text-slate-500">
                Confidence {pct(a.confidence_score)} · {result!.source_mode}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-slate-800">{a.direct_answer}</p>
            {a.evidence_summary && <p className="text-xs text-slate-500">{a.evidence_summary}</p>}
          </div>

          {a.supporting_events.length > 0 && (
            <div className="card">
              <div className="label">Supporting events</div>
              <div className="flex flex-wrap gap-1.5">
                {a.supporting_events.map((ev) => (
                  <EvidenceChip key={ev.event_id} ev={ev} projectId={projectId} />
                ))}
              </div>
            </div>
          )}

          {a.supporting_segments.length > 0 && (
            <div className="card">
              <div className="label">Supporting segments</div>
              <div className="flex flex-wrap gap-1.5">
                {a.supporting_segments.map((s) => (
                  <span key={s} className="chip border-slate-200 bg-slate-50 text-slate-600">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {a.simulated_interview_answers.length > 0 && (
            <div className="card space-y-2">
              <div className="flex items-center justify-between">
                <div className="label mb-0">Simulated interviews</div>
                <span className="chip border-amber-200 bg-amber-50 text-amber-700">Simulated personas · not real interviews</span>
              </div>
              {a.simulated_interview_answers.map((iv) => (
                <div key={iv.agent_id} className="rounded-lg border border-slate-200 p-3">
                  <div className="text-xs font-semibold text-slate-700">{iv.persona_label}</div>
                  <p className="mt-1 text-sm text-slate-700">{iv.answer}</p>
                  {iv.evidence_from_agent_memory.length > 0 && (
                    <ul className="mt-1 list-inside list-disc text-xs text-slate-500">
                      {iv.evidence_from_agent_memory.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {a.recommended_next_action.length > 0 && (
              <div className="card">
                <div className="label">Recommended next action</div>
                <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                  {a.recommended_next_action.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
            {a.limitations.length > 0 && (
              <div className="card">
                <div className="label">Limitations</div>
                <ul className="list-inside list-disc space-y-1 text-xs text-slate-500">
                  {a.limitations.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/workflow`}>
        ← Back to workflow
      </Link>
    </div>
  );
}
