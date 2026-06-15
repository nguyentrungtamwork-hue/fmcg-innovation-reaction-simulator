import { useEffect, useLayoutEffect, useState } from "react";
import { useTour } from "./TourProvider";
import { TOUR_DISCLAIMER } from "./tours";

interface Rect { top: number; left: number; width: number; height: number; }

export default function TourOverlay() {
  const { active, tour, index, step, next, prev, skip, finish } = useTour();
  const [rect, setRect] = useState<Rect | null>(null);

  const isLast = tour ? index >= tour.steps.length - 1 : false;
  const isFirst = index === 0;

  // Locate the spotlight target (if any) for the current step.
  useLayoutEffect(() => {
    if (!active || !step?.target_selector) {
      setRect(null);
      return;
    }
    const find = () => {
      const el = document.querySelector(step.target_selector!);
      if (el) {
        const r = el.getBoundingClientRect();
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
      } else {
        setRect(null);
      }
    };
    find();
    const t = window.setTimeout(find, 150); // allow route content to mount
    window.addEventListener("resize", find);
    window.addEventListener("scroll", find, true);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("resize", find);
      window.removeEventListener("scroll", find, true);
    };
  }, [active, step]);

  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skip();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, skip, next, prev]);

  if (!active || !step) return null;

  // Card position: near the target if found, else centered.
  const cardStyle: React.CSSProperties = rect
    ? {
        position: "fixed",
        top: Math.min(rect.top + rect.height + 12, window.innerHeight - 220),
        left: Math.min(Math.max(rect.left, 12), window.innerWidth - 340),
        maxWidth: 320,
      }
    : { position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)", maxWidth: 380 };

  return (
    <div className="fixed inset-0 z-[80]" role="dialog" aria-modal="true" aria-label={`Guided tour: ${tour?.name}`}>
      {/* dimmed backdrop; clicking it does not advance to avoid accidental skips */}
      <div className="absolute inset-0 bg-slate-900/50 motion-reduce:transition-none" />
      {/* spotlight ring around the target */}
      {rect && (
        <div
          className="pointer-events-none absolute rounded-lg ring-2 ring-brand-400"
          style={{
            top: rect.top - 6,
            left: rect.left - 6,
            width: rect.width + 12,
            height: rect.height + 12,
            boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.5)",
          }}
        />
      )}
      <div className="card relative z-[81] shadow-xl" style={cardStyle}>
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            {tour?.name} · {index + 1}/{tour?.steps.length}
          </span>
          <button className="text-xs text-slate-400 underline hover:text-slate-600" onClick={skip} aria-label="Skip tour">
            Skip
          </button>
        </div>
        <h3 className="text-base font-semibold text-slate-900">{step.title}</h3>
        <p className="mt-1 text-sm text-slate-600">{step.body}</p>
        {step.action_hint && <p className="mt-2 text-xs text-brand-700">💡 {step.action_hint}</p>}
        <div className="mt-3 flex items-center justify-between">
          <button className="btn-secondary" onClick={prev} disabled={isFirst}>
            Back
          </button>
          {isLast ? (
            <button className="btn-primary" onClick={finish}>Finish</button>
          ) : (
            <button className="btn-primary" onClick={next}>Next</button>
          )}
        </div>
        <p className="mt-3 text-[10px] leading-snug text-slate-400">{TOUR_DISCLAIMER}</p>
      </div>
    </div>
  );
}
