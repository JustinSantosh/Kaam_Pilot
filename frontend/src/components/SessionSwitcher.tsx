"use client";

import type { Customer } from "@/lib/api";
import { CheckIcon, PlusIcon } from "./icons";
import { Avatar } from "./ui";

export interface DemoCustomer extends Customer {
  id: string;
  city: string;
}

export const DEMO_CUSTOMERS: DemoCustomer[] = [
  { id: "ravi", name: "Ravi Kumar", phone: "+91 98260 11111", state: "CG", city: "Raipur" },
  { id: "asha", name: "Asha Mehta", phone: "+91 98200 22222", state: "MH", city: "Mumbai" },
  { id: "imran", name: "Imran Shaikh", phone: "+91 99000 33333", state: null, city: "State not given" },
];

export function SessionSwitcher({
  activeId,
  onSelect,
  onReset,
}: {
  activeId: string;
  onSelect: (id: string) => void;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        {DEMO_CUSTOMERS.map((c) => {
          const active = c.id === activeId;
          return (
            <button
              key={c.id}
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(c.id)}
              className={`flex min-h-15 w-full items-center gap-3 rounded-2xl border-2 px-3 py-2 text-left transition-colors ${
                active ? "border-ink bg-marigold-soft shadow-pop-sm" : "border-line bg-white hover:border-ink"
              }`}
            >
              <Avatar name={c.name} />
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="text-base font-extrabold">{c.name}</span>
                <span className={`text-[13px] font-semibold ${active ? "text-ink-700" : "text-ink-500"}`}>
                  {c.city}
                  {c.state ? ` · ${c.state}` : ""}
                </span>
              </span>
              {active && <CheckIcon size={20} strokeWidth={2.6} className="shrink-0 text-rani" />}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        onClick={onReset}
        className="flex min-h-11 items-center justify-center gap-2 rounded-[14px] border-2 border-dashed border-ink text-[15px] font-extrabold hover:bg-mist"
      >
        <PlusIcon size={18} strokeWidth={2.4} />
        New conversation
      </button>
    </div>
  );
}
