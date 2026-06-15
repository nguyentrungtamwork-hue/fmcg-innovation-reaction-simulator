import { useState } from "react";
import { tailorBriefing } from "../api/briefing";
import type { TailorOut } from "../types/api";
import ErrorState from "./ErrorState";
import LoadingState from "./LoadingState";
import { downloadText, titleCase } from "../utils/formatters";

const AUDIENCES = ["executive", "brand_team", "trade_sales", "rd_product", "consumer_insight"];
const TONES = ["concise", "boardroom", "working_session"];

export default function TailorTab({ projectId }: { projectId: string }) {
  const [audience, setAudience] = useState("brand_team");
  const [tone, setTone] = useState("concise");
  const [result, setResult] = useState<TailorOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setResult(await tailorBriefing(projectId, { audience, tone, include_evidence: true }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  const t = result?.tailored_payload;

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-end gap-3 print:hidden">
        <div>
          <label className="label" htmlFor="t-aud">Audience</label>
          <select id="t-aud" className="input py-1" value={audience} onChange={(e) => setAudience(e.target.value)}>
            {AUDIENCES.map((a) => <option key={a} value={a}>{titleCase(a)}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="t-tone">Tone</label>
          <select id="t-tone" className="input py-1" value={tone} onChange={(e) => setTone(e.target.value)}>
            {TONES.map((x) => <option key={x} value={x}>{titleCase(x)}</option>)}
          </select>
        </div>
        <button className="btn-primary" disabled={loading} onClick={run}>{loading ? "Tailoring…" : "Generate tailored briefing"}</button>
      </div>

      {loading && <LoadingState label="Re-framing for the audience…" />}
      {error ? <ErrorState error={error} /> : null}

      {t && !loading && (
        <div className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold text-slate-900">{t.headline}</h3>
            <div className="flex gap-2 print:hidden">
              <button className="btn-secondary" onClick={() => downloadText(`briefing-${audience}-${projectId}.md`, result!.markdown, "text/markdown")}>Download MD</button>
              <button className="btn-secondary" onClick={() => downloadText(`briefing-${audience}-${projectId}.json`, JSON.stringify(t, null, 2), "application/json")}>Download JSON</button>
              <button className="btn-primary" onClick={() => window.print()}>Print</button>
            </div>
          </div>
          <p className="text-sm text-slate-600"><span className="font-medium">Priority:</span> {t.audience_priority}</p>
          <Block title="What this audience needs to know" items={t.what_this_audience_needs_to_know} />
          <div className="grid gap-3 md:grid-cols-2">
            <Block title="Role-specific risks" items={t.role_specific_risks} />
            <Block title="Role-specific actions" items={t.role_specific_actions} />
            <Block title="Evidence to show" items={t.evidence_to_show} />
            <Block title="What not to overclaim" items={t.what_not_to_overclaim} />
          </div>
          <Block title="Talk track" items={t.talk_track} />
        </div>
      )}
    </div>
  );
}

function Block({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="label">{title}</div>
      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}
