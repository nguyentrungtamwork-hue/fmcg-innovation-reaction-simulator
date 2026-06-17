import { useState } from "react";

export function ReadOnlyBadge() {
  return (
    <span className="chip border-slate-300 bg-slate-100 text-slate-600" title="Local read-only presentation view">
      Read-only
    </span>
  );
}

export function PrintButton() {
  return (
    <button className="btn-secondary print-hide" onClick={() => window.print()}>
      Print / Save as PDF
    </button>
  );
}

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function DownloadMarkdownButton({ getMarkdown, name }: { getMarkdown: () => Promise<string>; name: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="btn-secondary print-hide"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          const md = await getMarkdown();
          download(`${name}_decision_pack.md`, md, "text/markdown");
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? "Preparing…" : "Download Markdown"}
    </button>
  );
}

export function DownloadJsonButton({ data, name }: { data: unknown; name: string }) {
  return (
    <button
      className="btn-secondary print-hide"
      onClick={() => download(`${name}_decision_pack.json`, JSON.stringify(data, null, 2), "application/json")}
    >
      Download JSON
    </button>
  );
}

export function CopyLinkButton() {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="btn-secondary print-hide"
      title="Copies this page URL. This is a local read-only view, not secure public sharing."
      onClick={async () => {
        try {
          await navigator.clipboard?.writeText(window.location.href);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable · ignore */
        }
      }}
    >
      {copied ? "Copied!" : "Copy local read-only link"}
    </button>
  );
}

export function DecisionPackSection({
  title,
  pageBreak,
  children,
}: {
  title: string;
  pageBreak?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className={`card decision-pack-section ${pageBreak ? "page-break" : ""}`} aria-label={title}>
      <h2 className="mb-2 text-base font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}
