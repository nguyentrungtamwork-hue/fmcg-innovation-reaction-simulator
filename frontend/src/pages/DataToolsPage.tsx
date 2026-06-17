import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  exportProjectBundle,
  getProjects,
  importProject,
  projectExportUrl,
  type ProjectImportResult,
} from "../api/projects";
import type { Project } from "../types/api";
import ErrorState from "../components/ErrorState";

/** Trigger a browser download of a JSON object. */
function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function DataToolsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState("");
  const [exporting, setExporting] = useState(false);
  const [includeLogs, setIncludeLogs] = useState(false);

  const [bundleText, setBundleText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ProjectImportResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    getProjects().then((p) => {
      setProjects(p);
      if (p.length && !selected) setSelected(p[0].id);
    }).catch(() => setProjects([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleExport() {
    if (!selected) return;
    setExporting(true);
    setError(null);
    try {
      const bundle = await exportProjectBundle(selected);
      const proj = projects.find((p) => p.id === selected);
      downloadJson(`${(proj?.name ?? "project").replace(/\s+/g, "_")}_export.json`, bundle);
    } catch (e) {
      setError(e);
    } finally {
      setExporting(false);
    }
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    file.text().then(setBundleText);
  }

  async function handleImport() {
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const bundle = JSON.parse(bundleText);
      const result = await importProject(bundle);
      setImportResult(result);
    } catch (e) {
      if (e instanceof SyntaxError) setError(new Error("That file is not valid JSON."));
      else setError(e);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="space-y-6" data-tour="data-tools-root">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Data Tools</h1>
        <p className="text-sm text-slate-500">
          Local/demo data management · export, import, back up, and reset project data. These tools
          operate on this local instance only; no cloud storage is involved.
        </p>
      </div>

      {error != null && <ErrorState error={error} />}

      {/* Export */}
      <section className="card space-y-3" aria-labelledby="export-h">
        <h2 id="export-h" className="text-base font-semibold text-slate-800">Export a project</h2>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="export-project" className="text-sm text-slate-500">Project</label>
          <select
            id="export-project"
            className="input max-w-xs py-1 text-sm"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {projects.length === 0 && <option value="">No projects</option>}
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <label className="flex items-center gap-1 text-xs text-slate-500">
            <input type="checkbox" checked={includeLogs} onChange={(e) => setIncludeLogs(e.target.checked)} />
            include logs
          </label>
          <button className="btn-primary" onClick={handleExport} disabled={!selected || exporting}>
            {exporting ? "Exporting…" : "Export project (JSON)"}
          </button>
          {selected && (
            <a
              className="btn-secondary"
              href={projectExportUrl(selected, { format: "zip", include_logs: includeLogs })}
            >
              Download .zip
            </a>
          )}
        </div>
        <p className="text-xs text-slate-400">
          The bundle includes project, brief, ontology, agents, events, reports, briefings, scenarios,
          snapshots, decisions, and live-run metadata. No secrets, API keys, or environment values.
        </p>
      </section>

      {/* Import */}
      <section className="card space-y-3" aria-labelledby="import-h">
        <h2 id="import-h" className="text-base font-semibold text-slate-800">Import / restore a project</h2>
        <input type="file" accept="application/json,.json" onChange={handleFile} aria-label="Import bundle file" />
        <textarea
          className="input h-32 w-full font-mono text-xs"
          placeholder="…or paste an exported bundle JSON here"
          value={bundleText}
          onChange={(e) => setBundleText(e.target.value)}
          aria-label="Import bundle JSON"
        />
        <button className="btn-primary" onClick={handleImport} disabled={!bundleText.trim() || importing}>
          {importing ? "Importing…" : "Import project"}
        </button>
        <p className="text-xs text-slate-400">
          Import always creates a <strong>new</strong> project with fresh IDs (overwrite is not supported).
        </p>
        {importResult && (
          <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">
            Imported as new project{" "}
            <Link className="underline" to={`/projects/${importResult.new_project_id}/home`}>
              {importResult.new_project_id.slice(0, 8)}…
            </Link>
            <ul className="mt-1 text-xs">
              {Object.entries(importResult.counts).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
            </ul>
          </div>
        )}
      </section>

      {/* Maintenance instructions */}
      <section className="card space-y-2 text-sm text-slate-600" aria-labelledby="maint-h">
        <h2 id="maint-h" className="text-base font-semibold text-slate-800">Backup, reset &amp; prune</h2>
        <p><strong>Backup SQLite:</strong> <code className="rounded bg-slate-100 px-1">python scripts/backup_sqlite.py</code> (add <code>--zip</code>) writes a timestamped copy to <code>backend/backups/</code>.</p>
        <p><strong>Reset demo data:</strong> <code className="rounded bg-slate-100 px-1">python scripts/reset_demo_data.py</code> deletes "FreshPlus Demo" projects (<code>--all --yes</code> wipes everything).</p>
        <p><strong>Prune logs:</strong> <code className="rounded bg-slate-100 px-1">python scripts/prune_app_logs.py</code> trims the app-log trail to its cap (<code>--older-than-days N</code> optional).</p>
        <p className="text-xs text-slate-400">
          See <code>docs/DATA_MANAGEMENT.md</code>. Open the footer <strong>Diagnostics</strong> drawer for live counts and recent errors.
        </p>
        <p className="text-sm"><Link className="text-brand-700 underline" to="/samples">Browse the Sample Library →</Link></p>
      </section>
    </div>
  );
}
