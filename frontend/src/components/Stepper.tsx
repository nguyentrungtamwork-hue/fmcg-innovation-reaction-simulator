export interface Step {
  id: number;
  title: string;
  done: boolean;
}

interface Props {
  steps: Step[];
  active: number;
  onSelect: (id: number) => void;
}

export default function Stepper({ steps, active, onSelect }: Props) {
  return (
    <ol className="flex flex-wrap gap-2">
      {steps.map((s) => {
        const isActive = s.id === active;
        return (
          <li key={s.id}>
            <button
              onClick={() => onSelect(s.id)}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition ${
                isActive
                  ? "border-brand-600 bg-brand-50 text-brand-800"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  s.done
                    ? "bg-emerald-500 text-white"
                    : isActive
                    ? "bg-brand-600 text-white"
                    : "bg-slate-200 text-slate-600"
                }`}
              >
                {s.done ? "✓" : s.id}
              </span>
              <span className="font-medium">{s.title}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
