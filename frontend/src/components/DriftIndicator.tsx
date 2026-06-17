import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSnapshots } from "../api/portfolio";
import { snapshotDiff } from "../api/history";
import type { SnapshotDiffOut } from "../types/api";
import { signed } from "../utils/formatters";

/** Shows how the active report drifted vs the latest snapshot. Silent if no snapshots. */
export default function DriftIndicator({ projectId }: { projectId: string }) {
  const [diff, setDiff] = useState<SnapshotDiffOut | null>(null);
  const [latestId, setLatestId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listSnapshots(projectId)
      .then((snaps) => {
        if (cancelled || snaps.length === 0) return;
        const latest = snaps[0].snapshot_id;
        setLatestId(latest);
        return snapshotDiff(projectId, { left: { type: "snapshot", snapshot_id: latest }, right: { type: "active_report" } });
      })
      .then((d) => {
        if (!cancelled && d) setDiff(d);
      })
      .catch(() => {
        /* no snapshots / not ready · stay silent */
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (!diff) return null;

  const overall = diff.scorecard_delta.overall_score?.delta ?? 0;
  const movers = diff.dimension_changes.filter((d) => d.direction !== "unchanged");
  const largest = movers.slice().sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0];
  const tone = overall > 0.5 ? "border-emerald-200 bg-emerald-50 text-emerald-800" : overall < -0.5 ? "border-red-200 bg-red-50 text-red-800" : "border-slate-200 bg-slate-50 text-slate-600";

  return (
    <div className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border p-2 text-sm print:hidden ${tone}`}>
      <span>
        Current report is <strong>{signed(overall, 1)}</strong> overall vs latest snapshot "{diff.left.name}".
        {largest ? ` Largest movement: ${largest.dimension.replace("_score", "").replace("_", " ")} (${signed(largest.delta, 1)}).` : " No dimension moved materially."}
      </span>
      <Link className="font-medium underline" to={`/projects/${projectId}/snapshots/diff${latestId ? `?left=${latestId}` : ""}`}>
        View full diff →
      </Link>
    </div>
  );
}
