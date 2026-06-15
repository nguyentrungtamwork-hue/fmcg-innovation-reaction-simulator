export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function num(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function signed(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const s = value.toFixed(digits);
  return value > 0 ? `+${s}` : s;
}

export function deltaTone(value: number): "up" | "down" | "flat" {
  if (value > 0.0005) return "up";
  if (value < -0.0005) return "down";
  return "flat";
}

export function titleCase(s: string): string {
  return s
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// --- consumer stance (FMCG analog of MiroFish SUPPORTIVE/NEUTRAL/OPPOSING) ---
// Derived purely from sentiment for display; it never changes scoring numbers.
export type Stance = "advocate" | "neutral" | "skeptic";

export function sentimentStance(value: number | null | undefined): Stance {
  const v = value ?? 0;
  if (v > 0.15) return "advocate";
  if (v < -0.05) return "skeptic";
  return "neutral";
}

export interface StanceMeta {
  label: string;
  /** chip classes for light surfaces */
  chip: string;
  /** solid node/dot fill (hex, for SVG) */
  fill: string;
  /** short caption */
  caption: string;
}

export const STANCE_META: Record<Stance, StanceMeta> = {
  advocate: { label: "Advocate", chip: "border-emerald-200 bg-emerald-50 text-emerald-700", fill: "#10b981", caption: "leans positive" },
  neutral: { label: "Neutral", chip: "border-slate-200 bg-slate-50 text-slate-600", fill: "#64748b", caption: "on the fence" },
  skeptic: { label: "Skeptic", chip: "border-rose-200 bg-rose-50 text-rose-700", fill: "#f43f5e", caption: "leans negative" },
};

export function stanceMeta(value: number | null | undefined): StanceMeta {
  return STANCE_META[sentimentStance(value)];
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function downloadText(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function numberFromRecord(rec: Record<string, unknown>, key: string): number | undefined {
  const v = rec[key];
  return typeof v === "number" ? v : undefined;
}
