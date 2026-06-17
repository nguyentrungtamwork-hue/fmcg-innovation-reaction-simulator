import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { deleteScenario, getScenario, listScenarios, runScenario } from "../api/scenarios";
import type { ScenarioListItem, ScenarioOverrides, ScenarioRunOut } from "../types/api";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import MetricCard from "../components/MetricCard";
import { deltaTone, num, pct, shortDate, signed, titleCase } from "../utils/formatters";

interface LeverDef {
  key: keyof ScenarioOverrides;
  label: string;
  min: number;
  max: number;
  step: number;
}

const NUMERIC_LEVERS: LeverDef[] = [
  { key: "price_change_pct", label: "Price change %", min: -30, max: 30, step: 1 },
  { key: "claim_credibility_boost", label: "Claim credibility boost", min: 0, max: 1, step: 0.1 },
  { key: "sampling_boost", label: "Sampling boost", min: 0, max: 1, step: 0.1 },
  { key: "promotion_boost", label: "Promotion boost", min: 0, max: 1, step: 0.1 },
  { key: "social_proof_boost", label: "Social proof boost", min: 0, max: 1, step: 0.1 },
  { key: "packaging_appeal_boost", label: "Packaging appeal boost", min: 0, max: 1, step: 0.1 },
  { key: "sensory_risk_reduction", label: "Sensory risk reduction", min: 0, max: 1, step: 0.1 },
  { key: "retailer_support_boost", label: "Retailer support boost", min: 0, max: 1, step: 0.1 },
  { key: "competitor_pressure_boost", label: "Competitor pressure boost", min: 0, max: 1, step: 0.1 },
];

const EMPTY_OVERRIDES: ScenarioOverrides = {
  price_change_pct: 0,
  claim_credibility_boost: 0,
  sampling_boost: 0,
  promotion_boost: 0,
  social_proof_boost: 0,
  packaging_appeal_boost: 0,
  sensory_risk_reduction: 0,
  retailer_support_boost: 0,
  competitor_pressure_boost: 0,
  channel_focus: null,
};

export default function ScenarioLabPage() {
  const { projectId = "" } = useParams();
  const [name, setName] = useState("10% price reduction");
  const [description, setDescription] = useState("");
  const [overrides, setOverrides] = useState<ScenarioOverrides>({ ...EMPTY_OVERRIDES, price_change_pct: -10 });
  const [channelFocus, setChannelFocus] = useState("");

  const [list, setList] = useState<ScenarioListItem[]>([]);
  const [selected, setSelected] = useState<ScenarioRunOut | null>(null);
  const [compareId, setCompareId] = useState<string>("");
  const [compareRun, setCompareRun] = useState<ScenarioRunOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [running, setRunning] = useState(false);
  const [loadingList, setLoadingList] = useState(true);

  async function refreshList() {
    setLoadingList(true);
    try {
      setList(await listScenarios(projectId));
    } catch (e) {
      setError(e);
    } finally {
      setLoadingList(false);
    }
  }

  useEffect(() => {
    void refreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function setLever(key: keyof ScenarioOverrides, value: number) {
    setOverrides((o) => ({ ...o, [key]: value }));
  }

  async function onRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await runScenario(projectId, {
        scenario_name: name.trim() || "Scenario",
        description: description.trim(),
        overrides: { ...overrides, channel_focus: channelFocus.trim() || null },
      });
      setSelected(result);
      await refreshList();
    } catch (e) {
      setError(e);
    } finally {
      setRunning(false);
    }
  }

  async function onSelect(id: string) {
    setError(null);
    setCompareId("");
    setCompareRun(null);
    try {
      setSelected(await getScenario(projectId, id));
    } catch (e) {
      setError(e);
    }
  }

  async function onCompare(id: string) {
    setCompareId(id);
    setCompareRun(null);
    if (!id) return;
    try {
      setCompareRun(await getScenario(projectId, id));
    } catch (e) {
      setError(e);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    try {
      await deleteScenario(projectId, id);
      if (selected?.scenario_id === id) setSelected(null);
      await refreshList();
    } catch (e) {
      setError(e);
    }
  }

  const mc = selected?.key_metric_changes;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Scenario Lab</h1>
        <p className="text-sm text-slate-500">
          Re-simulate the launch under what-if assumptions. The baseline simulation and report are preserved untouched.
        </p>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
        Exploratory decision support. Scenario deltas show the modelled <em>direction and magnitude</em> of change vs the baseline run · not a guaranteed market result. Baseline data is never modified.
      </div>

      {error ? <ErrorState error={error} /> : null}

      <div className="grid gap-5 lg:grid-cols-3">
        {/* form */}
        <section className="card space-y-3 lg:col-span-1">
          <h2 className="font-semibold text-slate-900">New scenario</h2>
          <div>
            <label className="label">Scenario name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" />
          </div>
          {NUMERIC_LEVERS.map((l) => {
            const v = (overrides[l.key] as number) ?? 0;
            return (
              <div key={l.key}>
                <div className="flex justify-between">
                  <label className="label mb-0">{l.label}</label>
                  <span className="text-xs font-medium text-slate-700">{l.key === "price_change_pct" ? `${v}%` : v.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  aria-label={l.label}
                  className="w-full accent-brand-600"
                  min={l.min}
                  max={l.max}
                  step={l.step}
                  value={v}
                  onChange={(e) => setLever(l.key, parseFloat(e.target.value))}
                />
              </div>
            );
          })}
          <div>
            <label className="label">Channel focus (optional)</label>
            <input className="input" value={channelFocus} onChange={(e) => setChannelFocus(e.target.value)} placeholder="e.g. tiktok" />
          </div>
          <div className="flex gap-2">
            <button className="btn-primary flex-1" disabled={running} onClick={onRun}>
              {running ? "Running…" : "Run scenario"}
            </button>
            <button
              className="btn-secondary"
              onClick={() => {
                setOverrides({ ...EMPTY_OVERRIDES });
                setChannelFocus("");
              }}
            >
              Reset
            </button>
          </div>
        </section>

        {/* results */}
        <section className="space-y-4 lg:col-span-2">
          {running && <LoadingState label="Re-simulating under the scenario…" />}

          {selected && (
            <div className="space-y-4">
              <div className="card">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">{selected.scenario_name}</h2>
                  <span className="text-xs text-slate-500">{shortDate(selected.created_at)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{selected.delta_summary}</p>
              </div>

              {mc && (
                <div className="grid gap-3 sm:grid-cols-4">
                  <MetricCard label="Trial prob. Δ" value={signed(mc.trial_probability_delta)} tone={deltaTone(mc.trial_probability_delta)} />
                  <MetricCard label="Repeat prob. Δ" value={signed(mc.repeat_probability_delta)} tone={deltaTone(mc.repeat_probability_delta)} />
                  <MetricCard label="Sentiment Δ" value={signed(mc.sentiment_delta)} tone={deltaTone(mc.sentiment_delta)} />
                  <MetricCard label="Trials Δ" value={signed(mc.trial_count_delta, 0)} tone={deltaTone(mc.trial_count_delta)} />
                  <MetricCard label="Purchase intent Δ" value={signed(mc.purchase_intent_delta)} tone={deltaTone(mc.purchase_intent_delta)} />
                  <MetricCard label="Recommends Δ" value={signed(mc.recommend_delta, 0)} tone={deltaTone(mc.recommend_delta)} />
                  <MetricCard label="Complaints Δ" value={signed(mc.complaint_delta, 0)} tone={deltaTone(-mc.complaint_delta)} />
                  <MetricCard label="Switching Δ" value={signed(mc.switch_delta, 0)} tone={deltaTone(-mc.switch_delta)} />
                </div>
              )}

              <div className="card">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="label mb-0">Baseline vs scenario{compareRun ? " (two-scenario compare)" : ""}</div>
                  {list.length > 1 && (
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-slate-500" htmlFor="cmp">Compare with</label>
                      <select
                        id="cmp"
                        className="input max-w-[14rem] py-1 text-xs"
                        value={compareId}
                        onChange={(e) => onCompare(e.target.value)}
                      >
                        <option value="">· none ·</option>
                        {list
                          .filter((s) => s.scenario_id !== selected.scenario_id)
                          .map((s) => (
                            <option key={s.scenario_id} value={s.scenario_id}>
                              {s.scenario_name}
                            </option>
                          ))}
                      </select>
                    </div>
                  )}
                </div>
                <ComparisonTable
                  baseline={selected.baseline_summary}
                  columns={[
                    { name: selected.scenario_name, summary: selected.scenario_summary },
                    ...(compareRun ? [{ name: compareRun.scenario_name, summary: compareRun.scenario_summary }] : []),
                  ]}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {selected.segment_changes.length > 0 && (
                  <div className="card">
                    <div className="label">Segment trial-probability changes</div>
                    <table className="w-full text-left text-sm">
                      <tbody>
                        {selected.segment_changes.slice(0, 8).map((s) => (
                          <tr key={s.segment_name} className="border-b border-slate-100">
                            <td className="py-1 pr-2 text-slate-700">{s.segment_name}</td>
                            <td className={`py-1 text-right font-medium ${tone(s.trial_probability_delta)}`}>
                              {signed(s.trial_probability_delta)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <ChangeChips title="Action distribution changes" data={selected.action_distribution_changes} />
              <ChangeChips title="Trigger changes" data={selected.trigger_changes} />
              <ChangeChips title="Barrier changes" data={selected.barrier_changes} />

              {selected.recommendation_changes.length > 0 && (
                <div className="card">
                  <div className="label">What this scenario implies</div>
                  <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                    {selected.recommendation_changes.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="card">
                <div className="label">Conclusion</div>
                <p className="text-sm text-slate-700">{selected.conclusion}</p>
              </div>
            </div>
          )}

          {/* saved scenarios */}
          <div className="card">
            <h2 className="mb-2 font-semibold text-slate-900">Saved scenarios</h2>
            {loadingList ? (
              <LoadingState label="Loading scenarios…" />
            ) : list.length === 0 ? (
              <p className="text-sm text-slate-500">No scenarios yet. Run one on the left.</p>
            ) : (
              <ul className="space-y-2">
                {list.map((s) => (
                  <li key={s.scenario_id} className="flex items-center justify-between rounded-lg border border-slate-200 p-2">
                    <button className="text-left" onClick={() => onSelect(s.scenario_id)}>
                      <div className="text-sm font-medium text-slate-800">{s.scenario_name}</div>
                      <div className="text-xs text-slate-500">
                        {s.scenario_event_count} scenario events · {shortDate(s.created_at)}
                      </div>
                    </button>
                    <div className="flex gap-2">
                      <button className="btn-secondary" onClick={() => onSelect(s.scenario_id)}>
                        View
                      </button>
                      <button className="btn-danger" onClick={() => onDelete(s.scenario_id)}>
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      <Link className="btn-secondary inline-flex" to={`/projects/${projectId}/workflow`}>
        ← Back to workflow
      </Link>
    </div>
  );
}

function tone(v: number) {
  return v > 0.0005 ? "text-emerald-600" : v < -0.0005 ? "text-red-600" : "text-slate-500";
}

const COMPARE_METRICS: { key: string; label: string; kind: "prob" | "count" }[] = [
  { key: "trial_probability", label: "Trial probability", kind: "prob" },
  { key: "purchase_intent", label: "Purchase intent", kind: "prob" },
  { key: "repeat_probability", label: "Repeat probability", kind: "prob" },
  { key: "sentiment", label: "Sentiment", kind: "prob" },
  { key: "complaint_count", label: "Complaints", kind: "count" },
  { key: "recommend_count", label: "Recommends", kind: "count" },
  { key: "switch_count", label: "Brand switches", kind: "count" },
];

interface CompareColumn {
  name: string;
  summary: Record<string, unknown>;
}

function ComparisonTable({ baseline, columns }: { baseline: Record<string, unknown>; columns: CompareColumn[] }) {
  const val = (rec: Record<string, unknown>, key: string): number | null =>
    typeof rec[key] === "number" ? (rec[key] as number) : null;
  const fmt = (v: number | null, kind: "prob" | "count") => (v === null ? "·" : kind === "count" ? String(v) : num(v, 3));

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-slate-500">
            <th className="py-1">Metric</th>
            <th className="py-1 text-right">Baseline</th>
            {columns.map((c) => (
              <th key={c.name} className="py-1 text-right">{c.name}</th>
            ))}
            {columns.map((c) => (
              <th key={`${c.name}-d`} className="py-1 text-right">Δ {columns.length > 1 ? c.name.split(" ")[0] : ""}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {COMPARE_METRICS.map((m) => {
            const b = val(baseline, m.key);
            return (
              <tr key={m.key} className="border-b border-slate-100">
                <td className="py-1 text-slate-700">{m.label}</td>
                <td className="py-1 text-right text-slate-500">{fmt(b, m.kind)}</td>
                {columns.map((c) => (
                  <td key={c.name} className="py-1 text-right font-medium text-slate-800">{fmt(val(c.summary, m.key), m.kind)}</td>
                ))}
                {columns.map((c) => {
                  const s = val(c.summary, m.key);
                  const d = b !== null && s !== null ? s - b : null;
                  // for complaints/switches, a decrease is good → invert tone
                  const toneVal = d === null ? 0 : m.key === "complaint_count" || m.key === "switch_count" ? -d : d;
                  return (
                    <td key={`${c.name}-d`} className={`py-1 text-right ${tone(toneVal)}`}>
                      {d === null ? "·" : signed(d, m.kind === "count" ? 0 : 3)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ChangeChips({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;
  return (
    <div className="card">
      <div className="label">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([k, v]) => (
          <span
            key={k}
            className={`chip ${v > 0 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-red-200 bg-red-50 text-red-700"}`}
          >
            {titleCase(k)} {v > 0 ? `+${v}` : v}
          </span>
        ))}
      </div>
    </div>
  );
}
