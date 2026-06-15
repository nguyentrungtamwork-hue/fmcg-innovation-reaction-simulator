// Tiny dependency-free SVG charts (Phase 11). No charting library.

interface LinePoint {
  x: number;
  y: number;
  label?: string;
}

export function MiniLineChart({
  points,
  width = 260,
  height = 90,
  color = "#2f5bea",
}: {
  points: LinePoint[];
  width?: number;
  height?: number;
  color?: string;
}) {
  if (points.length === 0) return <svg width={width} height={height} role="img" aria-label="empty chart" />;
  const pad = 18;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, minY + 0.0001);
  const sx = (x: number) => pad + ((x - minX) / (maxX - minX || 1)) * (width - 2 * pad);
  const sy = (y: number) => height - pad - ((y - minY) / (maxY - minY || 1)) * (height - 2 * pad);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");

  return (
    <svg width={width} height={height} role="img" aria-label="response curve" className="overflow-visible">
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#e2e8f0" />
      <path d={path} fill="none" stroke={color} strokeWidth={2} />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={sx(p.x)} cy={sy(p.y)} r={3} fill={color} />
          {p.label && (
            <text x={sx(p.x)} y={height - 4} fontSize={9} textAnchor="middle" fill="#64748b">
              {p.label}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}

export function MiniBarChart({
  bars,
  width = 260,
  height = 100,
}: {
  bars: { label: string; value: number }[];
  width?: number;
  height?: number;
}) {
  if (bars.length === 0) return <svg width={width} height={height} role="img" aria-label="empty chart" />;
  const pad = 18;
  const max = Math.max(...bars.map((b) => b.value), 0.0001);
  const bw = (width - 2 * pad) / bars.length;
  return (
    <svg width={width} height={height} role="img" aria-label="bar chart">
      {bars.map((b, i) => {
        const h = ((b.value / max) * (height - 2 * pad)) || 0;
        return (
          <g key={i}>
            <rect x={pad + i * bw + 2} y={height - pad - h} width={bw - 4} height={h} rx={2} fill="#2f5bea" />
            <text x={pad + i * bw + bw / 2} y={height - 4} fontSize={8} textAnchor="middle" fill="#64748b">
              {b.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ConfidenceGauge({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(1, value));
  const angle = -90 + pct * 180;
  const r = 52;
  const cx = 70;
  const cy = 70;
  const color = pct >= 0.75 ? "#059669" : pct >= 0.5 ? "#d97706" : "#dc2626";
  const arc = (start: number, end: number) => {
    const a0 = (start * Math.PI) / 180;
    const a1 = (end * Math.PI) / 180;
    return `M ${cx + r * Math.cos(a0)} ${cy + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(a1)} ${cy + r * Math.sin(a1)}`;
  };
  return (
    <svg width={140} height={92} role="img" aria-label={`confidence ${label}`}>
      <path d={arc(180, 360)} fill="none" stroke="#e2e8f0" strokeWidth={10} strokeLinecap="round" />
      <path d={arc(180, 180 + pct * 180)} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round" />
      <line
        x1={cx}
        y1={cy}
        x2={cx + (r - 8) * Math.cos((angle * Math.PI) / 180)}
        y2={cy + (r - 8) * Math.sin((angle * Math.PI) / 180)}
        stroke={color}
        strokeWidth={2.5}
      />
      <text x={cx} y={cy - 8} fontSize={18} textAnchor="middle" fontWeight="700" fill={color}>
        {Math.round(pct * 100)}
      </text>
      <text x={cx} y={cy + 8} fontSize={10} textAnchor="middle" fill="#64748b">
        {label.toUpperCase()}
      </text>
    </svg>
  );
}
