/** Small shadcn-style primitives, hand-written with Tailwind (no generator needed). Brand: D-027. */

import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { AlertIcon, CheckIcon, ClockIcon, SendIcon } from "./icons";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary: "border-ink bg-rani text-white shadow-pop-sm hover:bg-rani-700",
  secondary: "border-ink bg-white text-ink shadow-pop-sm hover:bg-mist",
  danger: "border-ink bg-white text-chilli shadow-pop-sm hover:bg-chilli-soft",
  ghost: "border-transparent bg-transparent text-ink-700 hover:bg-mist",
};

const SIZES: Record<Size, string> = {
  sm: "min-h-9 rounded-xl px-3 text-sm",
  md: "min-h-11 rounded-[14px] px-4 text-[15px]",
  lg: "min-h-12 rounded-[14px] px-5 text-base",
};

/** Sticker buttons: an ink outline and a hard shadow that drops away when pressed. */
export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 border-2 font-extrabold transition-[transform,box-shadow,background-color] active:translate-x-[3px] active:translate-y-[3px] active:shadow-none disabled:pointer-events-none disabled:opacity-55 disabled:shadow-none ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-[22px] border-2 border-ink bg-white ${className}`} {...props} />;
}

export function CardTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 pb-3 pt-4">
      <h2 className="font-display text-xl font-extrabold tracking-[-0.02em]">{children}</h2>
      {aside}
    </div>
  );
}

type Audience = "owner" | "customer";
type Chip = { label: string; className: string; icon?: "clock" | "send" | "check" };

const QUIET = "border-transparent";
const LOUD = "border-ink";

/** Owner-side labels say what happens next; only "needs your OK" and "accepted" are solid. */
const OWNER: Record<string, Chip> = {
  awaiting_approval: { label: "Needs your OK", className: `${LOUD} bg-marigold text-ink`, icon: "clock" },
  needs_clarification: { label: "Asking a detail", className: `${QUIET} bg-peacock-soft text-peacock-700` },
  busy: { label: "Owner is checking", className: `${QUIET} bg-marigold-soft text-ink` },
  draft: { label: "Draft", className: `${QUIET} bg-closed text-ink-700` },
  approved: { label: "Approved", className: `${QUIET} bg-leaf-soft text-leaf-700` },
  sent: { label: "Sent", className: `${QUIET} bg-leaf-soft text-leaf-700`, icon: "send" },
  followed_up: { label: "Nudged", className: `${QUIET} bg-iris-soft text-iris` },
  accepted: { label: "Accepted", className: `${LOUD} bg-leaf text-white`, icon: "check" },
  completed: { label: "Done", className: `${QUIET} bg-leaf-soft text-leaf-700` },
  rejected: { label: "Rejected", className: `${QUIET} bg-chilli-soft text-chilli` },
  rejected_input: { label: "Blocked", className: `${QUIET} bg-chilli-soft text-chilli` },
  cancelled: { label: "Cancelled", className: `${QUIET} bg-closed text-ink-700` },
  lapsed: { label: "Lapsed", className: `${QUIET} bg-closed text-ink-700` },
};

/** The customer sees the same states from their side of the counter. */
const CUSTOMER: Record<string, Chip> = {
  awaiting_approval: { label: "Owner is checking", className: `${QUIET} bg-marigold-soft text-ink`, icon: "clock" },
  busy: { label: "Owner is checking", className: `${QUIET} bg-marigold-soft text-ink`, icon: "clock" },
  rejected: { label: "Closed", className: `${QUIET} bg-closed text-ink-700` },
};

const ICONS = { clock: ClockIcon, send: SendIcon, check: CheckIcon };

export function statusLabel(status: string, audience: Audience = "owner") {
  return ((audience === "customer" && CUSTOMER[status]) || OWNER[status])?.label ?? status.replaceAll("_", " ");
}

export function StatusBadge({ status, audience = "owner" }: { status: string; audience?: Audience }) {
  const chip = (audience === "customer" && CUSTOMER[status]) || OWNER[status];
  const Icon = chip?.icon ? ICONS[chip.icon] : null;
  return (
    <span
      className={`inline-flex min-h-7 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border-2 px-2.5 text-xs font-extrabold ${
        chip?.className ?? `${QUIET} bg-closed text-ink-700`
      }`}
    >
      {Icon && <Icon size={13} strokeWidth={2.6} />}
      {chip?.label ?? status.replaceAll("_", " ")}
    </span>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-2xl border-2 border-ink bg-chilli-soft px-3.5 py-2.5 text-sm font-semibold text-chilli"
    >
      <AlertIcon size={18} className="mt-px shrink-0" />
      <span>{message}</span>
    </div>
  );
}

/** Initials in a coloured circle; the colour is stable per name. */
const AVATAR_COLORS = ["bg-marigold", "bg-peacock-pop", "bg-rani-pop", "bg-leaf-pop"];

export function Avatar({ name, size = "md", color }: { name: string; size?: "sm" | "md"; color?: string }) {
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "?";
  const hash = [...name].reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-full border-2 border-ink font-display font-extrabold text-ink ${
        size === "sm" ? "size-9 text-[13px]" : "size-10 text-[15px]"
      } ${color ?? AVATAR_COLORS[hash % AVATAR_COLORS.length]}`}
    >
      {initials}
    </span>
  );
}
