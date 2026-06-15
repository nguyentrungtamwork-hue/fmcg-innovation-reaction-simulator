import type { Scorecard } from "../types/api";
import { downloadText } from "../utils/formatters";

const DIMS: { key: keyof Scorecard; label: string; risk?: boolean }[] = [
  { key: "trial_potential_score", label: "Trial" },
  { key: "repeat_potential_score", label: "Repeat" },
  { key: "sentiment_score", label: "Sentiment" },
  { key: "advocacy_score", label: "Advocacy" },
  { key: "claim_credibility_score", label: "Claim credibility" },
  { key: "price_value_score", label: "Price/value" },
  { key: "channel_fit_score", label: "Channel fit" },
  { key: "risk_score", label: "Risk", risk: true },
  { key: "assumption_risk_score", label: "Assumption risk", risk: true },
  { key: "sensitivity_risk_score", label: "Sensitivity risk", risk: true },
];

function barColor(value: number, risk?: boolean): string {
  const good = risk ? 100 - value : value;
  return good >= 66 ? "bg-emerald-500" : good >= 40 ? "bg-amber-500" : "bg-red-500";
}

export default function ScorecardCard({ sc, exportable }: { sc: Scorecard; exportable?: boolean }) {
  return (
    <div className="card space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900">
            {sc.project_name}
            {sc.snapshot_name ? ` — ${sc.snapshot_name}` : ""}
          </div>
          <div className="text-xs text-slate-500">
            Confidence {sc.confidence_score.toFixed(2)} ({sc.confidence_label})
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-brand-700">{sc.overall_score}</div>
          <div className="text-[10px] uppercase tracking-wide text-slate-400">overall / 100</div>
        </div>
      </div>

      <ul className="space-y-1">
        {DIMS.map((d) => {
          const v = sc[d.key] as number;
          return (
            <li key={d.key}>
              <div className="flex justify-between text-xs">
                <span className="text-slate-600">{d.label}{d.risk ? " ↓" : ""}</span>
                <span className="font-medium text-slate-700">{v}</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded bg-slate-100">
                <div className={`h-full rounded ${barColor(v, d.risk)}`} style={{ width: `${Math.round(v)}%` }} />
              </div>
            </li>
          );
        })}
      </ul>

      <div className="text-xs text-slate-600">
        <div><span className="font-semibold">Next step:</span> {sc.recommended_next_step}</div>
        <div className="mt-1 text-[11px] text-slate-400">{sc.ranking_explanation}</div>
      </div>

      {exportable && (
        <div className="flex gap-2 print:hidden">
          <button
            className="btn-secondary"
            onClick={() => downloadText(`scorecard-${sc.snapshot_id ?? sc.project_id}.json`, JSON.stringify(sc, null, 2), "application/json")}
          >
            Scorecard JSON
          </button>
          <button
            className="btn-secondary"
            onClick={() => downloadText(`scorecard-${sc.snapshot_id ?? sc.project_id}.md`, scorecardMarkdown(sc), "text/markdown")}
          >
            Scorecard Markdown
          </button>
        </div>
      )}
      <p className="text-[11px] text-slate-400">{sc.disclaimer}</p>
    </div>
  );
}

export function scorecardMarkdown(sc: Scorecard): string {
  const rows: [string, string][] = [
    ["Overall score", `${sc.overall_score}/100`],
    ["Confidence", `${sc.confidence_score.toFixed(2)} (${sc.confidence_label})`],
    ["Trial potential", `${sc.trial_potential_score}/100`],
    ["Repeat potential", `${sc.repeat_potential_score}/100`],
    ["Sentiment", `${sc.sentiment_score}/100`],
    ["Advocacy", `${sc.advocacy_score}/100`],
    ["Claim credibility", `${sc.claim_credibility_score}/100`],
    ["Price/value", `${sc.price_value_score}/100`],
    ["Channel fit", `${sc.channel_fit_score}/100`],
    ["Risk (higher=worse)", `${sc.risk_score}/100`],
    ["Assumption risk", `${sc.assumption_risk_score}/100`],
    ["Sensitivity risk", `${sc.sensitivity_risk_score}/100`],
  ];
  const table = rows.map(([k, v]) => `| ${k} | ${v} |`).join("\n");
  const title = sc.project_name + (sc.snapshot_name ? ` — ${sc.snapshot_name}` : "");
  return (
    `# Concept Scorecard — ${title}\n\n| Metric | Score |\n| --- | --- |\n${table}\n\n` +
    `**Top opportunity:** ${sc.top_opportunity}\n\n**Top risk:** ${sc.top_risk}\n\n` +
    `**Recommended next step:** ${sc.recommended_next_step}\n\n` +
    `**Ranking:** ${sc.ranking_explanation}\n\n> ${sc.disclaimer}\n`
  );
}
