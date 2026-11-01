"use client";

import type { Customer } from "@/lib/api";
import { Button } from "./ui";

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
    <div className="space-y-2">
      {DEMO_CUSTOMERS.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          className={`w-full rounded-md border px-3 py-2 text-left transition-colors ${
            c.id === activeId
              ? "border-brand-500 bg-brand-50"
              : "border-slate-200 bg-white hover:bg-slate-50"
          }`}
        >
          <div className="text-sm font-medium text-slate-800">{c.name}</div>
          <div className="text-xs text-slate-500">
            {c.city}
            {c.state ? ` · ${c.state}` : ""}
          </div>
        </button>
      ))}
      <Button variant="ghost" className="w-full" onClick={onReset}>
        Start a new conversation
      </Button>
    </div>
  );
}
