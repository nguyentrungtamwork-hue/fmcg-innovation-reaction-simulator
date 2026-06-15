import { useState } from "react";
import { ApiError } from "../api/client";

const FRIENDLY: Record<string, string> = {
  project_not_found: "This project no longer exists.",
  brief_required: "Submit the innovation brief first (Step 2).",
  ontology_required: "Analyze the brief first (Step 3).",
  agents_required: "Generate agents first (Step 4).",
  events_required: "Run the simulation first (Step 5).",
  report_required: "Generate the strategic report first (Step 6).",
  baseline_events_required: "Run the baseline simulation before testing scenarios.",
  baseline_report_required: "Generate the baseline report before testing scenarios.",
  scenario_not_found: "That scenario could not be found.",
  briefing_required: "Generate the executive briefing first (Briefing tab).",
  board_summary_required: "Generate the board summary first.",
  snapshot_not_found: "That snapshot could not be found.",
  scorecard_required: "Generate the report/scorecard first.",
  ontology_not_found: "No ontology yet — analyze the brief first.",
  network_error: "Cannot reach the backend. Start it with `uvicorn app.main:app --reload`.",
};

export default function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  let code = "unknown_error";
  let message = "Something went wrong.";
  if (error instanceof ApiError) {
    code = error.code;
    message = FRIENDLY[error.code] ?? error.message;
    if (code === "network_error") message = "Backend is unreachable. Check the API URL or start the backend.";
  } else if (error instanceof Error) {
    message = error.message;
  }
  const requestId = error instanceof ApiError ? error.requestId : undefined;
  const [copied, setCopied] = useState(false);
  const copyRequestId = async () => {
    if (!requestId) return;
    try {
      await navigator.clipboard?.writeText(requestId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — ignore */
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800" role="alert">
      <span className="font-semibold">{message}</span>
      <span className="font-mono text-xs text-amber-600">({code})</span>
      {requestId && <span className="font-mono text-[10px] text-amber-500">Reference ID: {requestId}</span>}
      {requestId && (
        <button
          className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium hover:bg-amber-200"
          onClick={copyRequestId}
          aria-label="Copy request ID"
        >
          {copied ? "Copied!" : "Copy ID"}
        </button>
      )}
      {onRetry && (
        <button className="ml-auto rounded bg-amber-100 px-2 py-0.5 text-xs font-medium hover:bg-amber-200" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
