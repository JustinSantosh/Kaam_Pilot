/** Small shadcn-style primitives, hand-written with Tailwind (no generator needed). */

import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-600/50",
  secondary:
    "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400",
  danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-600/50",
  ghost: "text-slate-600 hover:bg-slate-100 disabled:text-slate-400",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`}
      {...props}
    />
  );
}

export function CardTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
      <h2 className="text-sm font-semibold text-slate-800">{children}</h2>
      {aside}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  awaiting_approval: "bg-amber-100 text-amber-800",
  needs_clarification: "bg-sky-100 text-sky-800",
  busy: "bg-amber-100 text-amber-800",
  draft: "bg-slate-100 text-slate-700",
  approved: "bg-emerald-100 text-emerald-800",
  sent: "bg-emerald-100 text-emerald-800",
  followed_up: "bg-violet-100 text-violet-800",
  accepted: "bg-emerald-200 text-emerald-900",
  completed: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  rejected_input: "bg-red-100 text-red-800",
  cancelled: "bg-slate-200 text-slate-700",
  lapsed: "bg-slate-200 text-slate-700",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </div>
  );
}
