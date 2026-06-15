interface Props {
  label: string;
  value: string;
  hint?: string;
  tone?: "up" | "down" | "flat" | "neutral";
}

const toneClass: Record<string, string> = {
  up: "text-emerald-600",
  down: "text-red-600",
  flat: "text-slate-500",
  neutral: "text-slate-900",
};

export default function MetricCard({ label, value, hint, tone = "neutral" }: Props) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={`text-2xl font-semibold ${toneClass[tone]}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}
