import { PIPELINE_STAGES, STAGE_LABELS, type PipelineBoardFilters } from "../../api/pipeline";

const DECISION_LABELS = ["go", "validate", "revise", "hold", "incomplete"];

export default function PipelineFilterBar({
  filters,
  matched,
  total,
  onChange,
  onClear,
}: {
  filters: PipelineBoardFilters;
  matched: number;
  total: number;
  onChange: (f: PipelineBoardFilters) => void;
  onClear: () => void;
}) {
  function set<K extends keyof PipelineBoardFilters>(key: K, value: PipelineBoardFilters[K]) {
    const next = { ...filters };
    if (value === undefined || value === "" || (typeof value === "boolean" && value === true && key === "include_archived")) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(next);
  }

  const activeCount = Object.keys(filters).length;

  return (
    <div className="card flex flex-wrap items-end gap-2" aria-label="Pipeline filters">
      <div>
        <label htmlFor="pf-search" className="label">Search</label>
        <input
          id="pf-search"
          className="input max-w-[14rem] py-1 text-sm"
          placeholder="Project name…"
          value={filters.search ?? ""}
          onChange={(e) => set("search", e.target.value || undefined)}
        />
      </div>
      <div>
        <label htmlFor="pf-stage" className="label">Stage</label>
        <select
          id="pf-stage"
          className="input max-w-[10rem] py-1 text-sm"
          value={filters.stage ?? ""}
          onChange={(e) => set("stage", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {PIPELINE_STAGES.map((s) => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="pf-label" className="label">Decision</label>
        <select
          id="pf-label"
          className="input max-w-[10rem] py-1 text-sm"
          value={filters.decision_label ?? ""}
          onChange={(e) => set("decision_label", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {DECISION_LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="pf-min" className="label">Min score</label>
        <input
          id="pf-min"
          type="number"
          min={0}
          max={100}
          className="input w-20 py-1 text-sm"
          value={filters.min_score ?? ""}
          onChange={(e) => set("min_score", e.target.value === "" ? undefined : Number(e.target.value))}
        />
      </div>
      <div>
        <label htmlFor="pf-risk" className="label">Max risk</label>
        <input
          id="pf-risk"
          type="number"
          min={0}
          max={100}
          className="input w-20 py-1 text-sm"
          value={filters.max_risk ?? ""}
          onChange={(e) => set("max_risk", e.target.value === "" ? undefined : Number(e.target.value))}
        />
      </div>
      <div>
        <label htmlFor="pf-owner" className="label">Owner team</label>
        <input
          id="pf-owner"
          className="input max-w-[12rem] py-1 text-sm"
          placeholder="e.g. R&D"
          value={filters.owner_team ?? ""}
          onChange={(e) => set("owner_team", e.target.value || undefined)}
        />
      </div>
      <label className="flex items-center gap-1 pb-1 text-xs text-slate-500">
        <input
          type="checkbox"
          checked={filters.include_archived !== false}
          onChange={(e) => set("include_archived", e.target.checked ? undefined : false)}
        />
        Include archived
      </label>
      <button className="btn-secondary ml-auto" onClick={onClear} disabled={activeCount === 0}>
        Clear filters
      </button>
      <span className="text-xs text-slate-500">
        Showing <strong>{matched}</strong> of {total}
      </span>
    </div>
  );
}
