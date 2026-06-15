interface Props {
  ready: boolean;
  label: string;
}

export default function StatusBadge({ ready, label }: Props) {
  return (
    <span
      className={`chip ${
        ready
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-slate-200 bg-slate-50 text-slate-500"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${ready ? "bg-emerald-500" : "bg-slate-300"}`} />
      {label}
    </span>
  );
}
