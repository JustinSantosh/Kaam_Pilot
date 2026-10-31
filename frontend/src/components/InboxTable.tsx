"use client";

import type { QuoteSummary } from "@/lib/api";
import { formatPaise } from "@/lib/money";
import { StatusBadge } from "./ui";

export type InboxFilter = "awaiting_approval" | "open" | "closed" | "all";

const FILTERS: { id: InboxFilter; label: string }[] = [
  { id: "awaiting_approval", label: "Needs review" },
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
      <div className="flex gap-1 border-b border-slate-100 px-3 py-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => onFilter(f.id)}
            className={`rounded px-2 py-1 text-xs font-medium ${
              filter === f.id ? "bg-brand-50 text-brand-700" : "text-slate-500 hover:bg-slate-100"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {quotes.length === 0 ? (
        <p className="px-4 py-10 text-center text-sm text-slate-500">
          Nothing here. Send a scenario from the Customer Hub.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {quotes.map((q) => (
            <li key={q.quote_id}>
              <button
                onClick={() => onSelect(q.quote_id)}
                className={`w-full px-3 py-2.5 text-left transition-colors ${
                  q.quote_id === selectedId ? "bg-brand-50" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">
                    {q.customer_name || "Customer"}
                  </span>
                  <span className="text-sm font-semibold tabular-nums text-slate-800">
                    {formatPaise(q.total_paise)}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-500">
                  <span>
                    {q.number} · R{q.revision} · {q.item_count} item{q.item_count === 1 ? "" : "s"}{" "}
                    · {age(q.created_at)} ago
                  </span>
                  <StatusBadge status={q.status} />
                </div>
                {q.flags.length > 0 && (
                  <div className="mt-1 text-[11px] text-amber-700">⚠ needs a check</div>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
