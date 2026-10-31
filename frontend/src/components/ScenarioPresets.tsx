"use client";

import type { Scenario } from "@/lib/api";

export function ScenarioPresets({
  scenarios,
  disabled,
  onSend,
}: {
  scenarios: Scenario[];
  disabled: boolean;
  onSend: (message: string) => void;
}) {
  if (!scenarios.length) {
    return <p className="text-xs text-slate-500">Presets load from the backend.</p>;
  }
  return (
    <div className="space-y-2">
      {scenarios.map((s) => (
        <div key={s.id} className="rounded-md border border-slate-200 bg-white p-2">
          <button
            disabled={disabled}
            onClick={() => onSend(s.message)}
            className="w-full text-left disabled:opacity-50"
            title={s.message}
          >
            <div className="text-sm font-medium text-slate-800">{s.label}</div>
            <div className="line-clamp-2 text-xs text-slate-500">{s.message}</div>
          </button>
          {s.follow_up && (
            <button
              disabled={disabled}
              onClick={() => onSend(s.follow_up!)}
              className="mt-1.5 w-full rounded bg-slate-50 px-2 py-1 text-left text-xs text-brand-600 hover:bg-brand-50 disabled:opacity-50"
              title={s.follow_up}
            >
              ↳ Send follow-up: {s.follow_up}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
