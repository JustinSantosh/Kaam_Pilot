"use client";

import type { QuoteSummary } from "@/lib/api";
import { formatPaise } from "@/lib/money";
import { AlertIcon } from "./icons";
import { Avatar, StatusBadge } from "./ui";

export type InboxFilter = "awaiting_approval" | "open" | "closed" | "all";

const FILTERS: { id: InboxFilter; label: string }[] = [
  { id: "awaiting_approval", label: "Needs your OK" },
  { id: "open", label: "Open" },
  { id: "closed", label: "Closed" },
  { id: "all", label: "All" },
];

function age(iso: string) {
  const ms = Date.now() - new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  const min = Math.max(0, Math.round(ms / 60000));
  if (min < 60) return `${min}m`;
  const h = Math.round(min / 60);
  return h < 48 ? `${h}h` : `${Math.round(h / 24)}d`;
}

export function InboxTable({
  quotes,
  filter,
  onFilter,
  selectedId,
  onSelect,
}: {
  quotes: QuoteSummary[];
  filter: InboxFilter;
  onFilter: (f: InboxFilter) => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap gap-1.5 border-b-2 border-ink px-3.5 pb-3.5">
        {FILTERS.map((f) => {
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              type="button"
              aria-pressed={active}
              onClick={() => onFilter(f.id)}
              className={`min-h-11 rounded-xl border-2 px-2.5 text-sm font-extrabold transition-colors ${
                active ? "border-ink bg-ink text-white" : "border-line bg-white hover:border-ink"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>
      {quotes.length === 0 ? (
        <p className="px-5 py-12 text-center text-[15px] font-semibold text-ink-500">
          {filter === "awaiting_approval"
            ? "Sab clear! No quotes are waiting for you."
            : "Nothing here yet. Send a scenario from the Customer Hub."}
        </p>
      ) : (
        <ul className="divide-y-[1.5px] divide-line">
          {quotes.map((q) => {
            const selected = q.quote_id === selectedId;
            return (
              <li key={q.quote_id}>
                <button
                  type="button"
                  aria-current={selected ? "true" : undefined}
                  onClick={() => onSelect(q.quote_id)}
                  className={`flex w-full flex-col gap-2 px-4.5 py-3.5 text-left transition-colors ${
                    selected ? "bg-marigold-soft shadow-[inset_0_0_0_2px_var(--color-ink)]" : "hover:bg-mist"
                  }`}
                >
                  <span className="flex w-full items-center gap-2.5">
                    <Avatar name={q.customer_name || "Customer"} size="sm" />
                    <span className="min-w-0 flex-1 truncate text-base font-extrabold">
                      {q.customer_name || "Customer"}
                    </span>
                    <span className="text-base font-extrabold tabular-nums">{formatPaise(q.total_paise)}</span>
                  </span>
                  <span className="flex w-full flex-wrap items-center justify-between gap-x-2.5 gap-y-1.5 pl-11.5">
                    <span className={`text-[13px] font-semibold ${selected ? "text-ink-700" : "text-ink-500"}`}>
                      {q.number} · R{q.revision} · {q.item_count} item{q.item_count === 1 ? "" : "s"} ·{" "}
                      {age(q.created_at)} ago
                    </span>
                    <StatusBadge status={q.status} />
                  </span>
                  {q.flags.length > 0 && (
                    <span className="ml-11.5 inline-flex w-fit items-center gap-1.5 rounded-full bg-chilli-soft px-2.5 py-0.5 text-xs font-extrabold text-chilli">
                      <AlertIcon size={13} strokeWidth={2.4} />
                      Needs a check
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
