import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getDecisionBoard, getDecisionBoardMarkdown } from "../api/portfolio";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import {
  DecisionPackSection,
  DownloadJsonButton,
  DownloadMarkdownButton,
  PrintButton,
  ReadOnlyBadge,
} from "../components/decisionpack/DecisionPackParts";
import { titleCase } from "../utils/formatters";

type Board = Record<string, any>;

const LABELS = ["go", "validate", "revise", "hold", "incomplete"] as const;
const LABEL_TONE: Record<string, string> = {
  go: "border-emerald-200 bg-emerald-50 text-emerald-700",
  validate: "border-amber-200 bg-amber-50 text-amber-700",
  revise: "border-orange-200 bg-orange-50 text-orange-700",
  hold: "border-rose-200 bg-rose-50 text-rose-700",
  incomplete: "border-slate-200 bg-slate-50 text-slate-500",
};

function num(v: unknown) {
  return v == null ? "·" : typeof v === "number" ? Math.round(v) : String(v);
}

export default function PortfolioDecisionBoardPage() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    getDecisionBoard().then(setBoard).catch(setError).finally(() => setLoading(false));
  }, []);

  const items: any[] = board?.items ?? [];
  const filteredItems = useMemo(
    () => (filter ? items.filter((it) => it.decision_label === filter) : items),
    [items, filter]
  );

  if (loading) return <LoadingState label="Building decision board…" />;
  if (error) return <ErrorState error={error} />;
  if (!board) return null;

  const s = board.summary ?? {};

  return (
    <div className="decision-pack space-y-4">
      <div className="card decision-pack-section">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h1 className="text-2xl font-semibold text-slate-900">Portfolio Decision Board</h1>
              <ReadOnlyBadge />
            </div>
            <div className="text-xs text-slate-400">Generated {String(board.generated_at ?? "").slice(0, 10)} · {s.total_projects ?? 0} project(s)</div>
          </div>
          <div className="flex flex-wrap gap-2 print-hide">
            <PrintButton />
            <DownloadMarkdownButton getMarkdown={getDecisionBoardMarkdown} name="portfolio" />
            <DownloadJsonButton data={board} name="portfolio" />
            <Link className="btn-secondary" to="/portfolio/pipeline">Apply labels to Pipeline →</Link>
            <Link className="btn-secondary" to="/portfolio">← Portfolio</Link>
          </div>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {LABELS.map((l) => (
            <MetricCard key={l} label={titleCase(l)} value={String(s[`${l}_count`] ?? 0)} />
          ))}
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <MetricCard label="Top concept" value={s.top_project ?? "·"} />
          <MetricCard label="Highest risk" value={s.highest_risk_project ?? "·"} />
        </div>
        <p className="mt-3 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-slate-700">
          {board.portfolio_recommendation}
        </p>
      </div>

      <DecisionPackSection title="Decision Board">
        <div className="mb-2 flex flex-wrap items-center gap-2 print-hide">
          <span className="text-xs text-slate-500">Filter:</span>
          <button className={`chip ${!filter ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-slate-50 text-slate-500"}`} onClick={() => setFilter("")}>All</button>
          {LABELS.map((l) => (
            <button key={l} className={`chip ${filter === l ? LABEL_TONE[l] : "border-slate-200 bg-slate-50 text-slate-500"}`} onClick={() => setFilter(l)}>
              {titleCase(l)}
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500">
                <th className="px-2 py-1">Project</th>
                <th className="px-2">Decision</th>
                <th className="px-2">Overall</th>
                <th className="px-2">Conf</th>
                <th className="px-2">Trial</th>
                <th className="px-2">Repeat</th>
                <th className="px-2">Risk</th>
                <th className="px-2">Top opportunity</th>
                <th className="px-2">Top risk</th>
                <th className="px-2">Next step</th>
                <th className="px-2">Owner</th>
                <th className="px-2 print-hide">Pack</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((it) => (
                <tr key={it.project_id} className="border-b border-slate-100 align-top">
                  <td className="px-2 py-1 font-medium text-slate-800">{it.project_name}</td>
                  <td className="px-2"><span className={`chip ${LABEL_TONE[it.decision_label]}`}>{titleCase(it.decision_label)}</span></td>
                  <td className="px-2">{num(it.overall_score)}</td>
                  <td className="px-2">{it.confidence_label ?? "·"}</td>
                  <td className="px-2">{num(it.trial_potential_score)}</td>
                  <td className="px-2">{num(it.repeat_potential_score)}</td>
                  <td className="px-2">{num(it.risk_score)}</td>
                  <td className="px-2 text-xs text-slate-600">{it.top_opportunity ?? "·"}</td>
                  <td className="px-2 text-xs text-slate-600">{it.top_risk ?? "·"}</td>
                  <td className="px-2 text-xs text-slate-600">{it.recommended_next_step}</td>
                  <td className="px-2 text-xs text-slate-500">{it.owner_team}</td>
                  <td className="px-2 print-hide">
                    {it.has_decision_pack ? (
                      <Link className="text-xs font-medium text-brand-700 hover:underline" to={it.decision_pack_url}>Decision Pack →</Link>
                    ) : (
                      <span className="text-xs text-slate-400">·</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DecisionPackSection>

      <DecisionPackSection title="Decision Buckets">
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {LABELS.map((l) => {
            const bucket = items.filter((it) => it.decision_label === l);
            return (
              <div key={l} className="rounded-lg border border-slate-200 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <span className={`chip ${LABEL_TONE[l]}`}>{titleCase(l)}</span>
                  <span className="text-xs text-slate-400">{bucket.length}</span>
                </div>
                <ul className="text-sm text-slate-700">
                  {bucket.length === 0 ? <li className="text-xs text-slate-400">None</li> : bucket.map((it) => <li key={it.project_id}>{it.project_name}</li>)}
                </ul>
              </div>
            );
          })}
        </div>
      </DecisionPackSection>

      <DecisionPackSection title="Rankings" pageBreak>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {[
            ["best_overall", "Best overall"],
            ["best_trial", "Best trial"],
            ["best_repeat", "Best repeat"],
            ["lowest_risk", "Lowest risk"],
            ["highest_confidence", "Highest confidence"],
          ].map(([key, label]) => (
            <div key={key} className="rounded-lg border border-slate-200 p-3">
              <div className="label">{label}</div>
              <ol className="list-inside list-decimal text-sm text-slate-700">
                {(board.rankings?.[key] ?? []).map((r: any, i: number) => (
                  <li key={i}>{r.project_name} <span className="text-xs text-slate-400">({r.value})</span></li>
                ))}
                {(board.rankings?.[key] ?? []).length === 0 && <li className="list-none text-xs text-slate-400">No report-ready projects.</li>}
              </ol>
            </div>
          ))}
        </div>
      </DecisionPackSection>

      <DecisionPackSection title="Limitations">
        <ul className="list-inside list-disc text-xs text-slate-500">
          {(board.limitations ?? []).map((l: string, i: number) => <li key={i}>{l}</li>)}
        </ul>
      </DecisionPackSection>

      <p className="text-center text-[11px] text-slate-400">
        Portfolio decisions are heuristic decision-support outputs, not validated market forecasts.
      </p>
    </div>
  );
}
