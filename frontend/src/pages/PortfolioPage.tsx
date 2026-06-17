import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getPortfolio } from "../api/portfolio";
import type { PortfolioOut, PortfolioProjectRow } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import { num } from "../utils/formatters";

type SortKey = "overall_score" | "trial_potential_score" | "repeat_potential_score" | "risk_score" | "confidence_score";
type FilterKey = "all" | "report_ready" | "high_risk" | "low_confidence" | "needs_validation";

export default function PortfolioPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<PortfolioOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<SortKey>("overall_score");
  const [filter, setFilter] = useState<FilterKey>("all");

  useEffect(() => {
    getPortfolio()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    let r = [...data.projects];
    if (filter === "report_ready") r = r.filter((p) => p.has_report);
    if (filter === "high_risk") r = r.filter((p) => (p.risk_score ?? 0) >= 55);
    if (filter === "low_confidence") r = r.filter((p) => (p.confidence_score ?? 1) < 0.5);
    if (filter === "needs_validation") r = r.filter((p) => (p.confidence_score ?? 1) < 0.6 || (p.risk_score ?? 0) >= 55);
    r.sort((a, b) => (Number(b[sort] ?? -1) - Number(a[sort] ?? -1)));
    return r;
  }, [data, sort, filter]);

  if (loading) return <LoadingState label="Loading portfolio…" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  const s = data.summary;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Innovation portfolio</h1>
          <p className="text-sm text-slate-500">Compare concepts by heuristic scorecard. Decision support, not a forecast.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-primary" to="/portfolio/decision-board">Decision Board →</Link>
          <Link className="btn-secondary" to="/compare">Compare concepts →</Link>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <MetricCard label="Projects" value={String(s.total_projects)} />
        <MetricCard label="Report-ready" value={String(s.report_ready_projects)} />
        <MetricCard label="Top concept" value={s.highest_score_project ?? "·"} tone="up" />
        <MetricCard label="Highest risk" value={s.highest_risk_project ?? "·"} tone="down" />
      </div>

      <div className="card">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-500" htmlFor="sort">Sort</label>
            <select id="sort" className="input max-w-[12rem] py-1 text-sm" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
              <option value="overall_score">Overall score</option>
              <option value="trial_potential_score">Trial potential</option>
              <option value="repeat_potential_score">Repeat potential</option>
              <option value="risk_score">Risk</option>
              <option value="confidence_score">Confidence</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-500" htmlFor="filter">Filter</label>
            <select id="filter" className="input max-w-[12rem] py-1 text-sm" value={filter} onChange={(e) => setFilter(e.target.value as FilterKey)}>
              <option value="all">All</option>
              <option value="report_ready">Report ready</option>
              <option value="high_risk">High risk</option>
              <option value="low_confidence">Low confidence</option>
              <option value="needs_validation">Needs validation</option>
            </select>
          </div>
        </div>

        {rows.length === 0 ? (
          <p className="text-sm text-slate-500">No projects match. Create one from the Projects page and run its workflow.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-2">Concept</th>
                  <th className="px-2">Overall</th>
                  <th className="px-2">Conf.</th>
                  <th className="px-2">Trial</th>
                  <th className="px-2">Repeat</th>
                  <th className="px-2">Risk</th>
                  <th className="px-2">Top opportunity</th>
                  <th className="px-2">Recommended next step</th>
                  <th className="px-2"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.project_id} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50" onClick={() => navigate(`/projects/${p.project_id}/workflow`)}>
                    <td className="py-2 pr-2 font-medium text-slate-800">{p.project_name}</td>
                    <td className="px-2 font-semibold text-brand-700">{p.overall_score ?? "·"}</td>
                    <td className="px-2">{p.confidence_score != null ? num(p.confidence_score, 2) : "·"}</td>
                    <td className="px-2">{p.trial_potential_score ?? "·"}</td>
                    <td className="px-2">{p.repeat_potential_score ?? "·"}</td>
                    <td className="px-2">{p.risk_score ?? "·"}</td>
                    <td className="px-2 text-xs text-slate-600">{p.top_opportunity ?? (p.has_report ? "·" : "No report yet")}</td>
                    <td className="px-2 text-xs text-slate-600">{p.recommended_next_step ?? "·"}</td>
                    <td className="px-2 text-right">
                      {p.has_report && (
                        <span className="flex justify-end gap-2">
                          <Link
                            className="text-xs font-medium text-brand-700 hover:underline"
                            to={`/projects/${p.project_id}/briefing`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            Briefing →
                          </Link>
                          <Link
                            className="text-xs font-medium text-brand-700 hover:underline"
                            to={`/projects/${p.project_id}/decision-pack`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            Decision Pack →
                          </Link>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
