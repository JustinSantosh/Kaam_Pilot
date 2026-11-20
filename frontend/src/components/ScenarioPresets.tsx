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
    return <p className="text-[13px] font-semibold text-ink-500">Presets load from the backend.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {scenarios.map((s) => (
        <div key={s.id} className="flex flex-col gap-1.5">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onSend(s.message)}
            title={s.message}
            className="flex w-full flex-col gap-0.5 rounded-[14px] border-[1.5px] border-line bg-mist px-3 py-2.5 text-left transition-colors hover:border-ink hover:bg-white disabled:opacity-55"
          >
            <span className="text-[15px] font-extrabold">{s.label}</span>
            <span className="w-full truncate text-[13px] leading-snug text-ink-700">{s.message}</span>
          </button>
          {s.follow_up && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSend(s.follow_up!)}
              title={s.follow_up}
              className="ml-3.5 flex min-h-11 items-center rounded-xl bg-peacock-soft px-3 text-left text-[13px] font-extrabold text-peacock-700 transition-colors hover:bg-[#c4efeb] disabled:opacity-55"
            >
              <span className="min-w-0 truncate">↳ Send follow-up: {s.follow_up}</span>
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
