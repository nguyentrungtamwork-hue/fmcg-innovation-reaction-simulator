import { useState } from "react";
import { generateBoardSummary } from "../api/briefing";
import type { BoardSummaryOut } from "../types/api";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import { downloadText } from "../utils/formatters";

export default function BoardSummaryTab({ projectId }: { projectId: string }) {
  const [result, setResult] = useState<BoardSummaryOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(await generateBoardSummary(projectId));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  const s = result?.summary_payload;

  return (
    <div className="space-y-4">
      <div className="card flex items-center justify-between print:hidden">
        <p className="text-sm text-slate-500">A one-page summary suitable for a board slide.</p>
        <button className="btn-primary" disabled={loading} onClick={run}>{loading ? "Generating…" : result ? "Regenerate" : "Generate board summary"}</button>
      </div>

      {loading && <LoadingState label="Building the one-pager…" />}
      {error ? <ErrorState error={error} /> : null}

      {s && !loading && (
        <div className="card space-y-3">
          <div className="rounded-lg border border-brand-200 bg-brand-50 p-3">
            <div className="text-xs uppercase tracking-wide text-brand-700">{s.decision_status.replace("_", " ")}</div>
            <div className="text-lg font-semibold text-slate-900">{s.headline_recommendation}</div>
            <div className="text-sm text-slate-600">{s.one_sentence_concept}</div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <Card title="3 key findings" items={s.three_key_findings} />
            <Card title="Top 3 risks" items={s.top_three_risks} tone="red" />
            <Card title="Next 3 actions" items={s.next_three_actions} tone="emerald" />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Card title="Decision gate" items={[s.decision_gate]} />
            <Card title="Validation needed" items={s.validation_needed} />
          </div>
          <p className="text-xs text-slate-500">{s.confidence_and_caveat}</p>
          <div className="flex gap-2 print:hidden">
            <button className="btn-secondary" onClick={() => downloadText(`board-summary-${projectId}.md`, result!.markdown, "text/markdown")}>Download Markdown</button>
            <button className="btn-secondary" onClick={() => downloadText(`board-summary-${projectId}.json`, JSON.stringify(s, null, 2), "application/json")}>Download JSON</button>
            <button className="btn-primary" onClick={() => window.print()}>Print</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ title, items, tone }: { title: string; items: string[]; tone?: string }) {
  const border = tone === "red" ? "border-red-100" : tone === "emerald" ? "border-emerald-100" : "border-slate-200";
  return (
    <div className={`rounded-lg border ${border} p-3`}>
      <div className="label">{title}</div>
      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}
