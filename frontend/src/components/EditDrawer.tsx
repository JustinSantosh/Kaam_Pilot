"use client";

import { useState } from "react";
import type { CatalogOption, Decision, QuoteDetail } from "@/lib/api";
import { PlusIcon } from "./icons";
import { Modal } from "./Modal";
import { Button } from "./ui";

interface Line {
  key: number;
  sku: string;
  quantity: number;
  specs: Record<string, string>;
}

type DiscountMode = "none" | "flat" | "percent";

const LABEL = "text-xs font-extrabold text-ink-700";
const FIELD_BASE =
  "mt-1 block min-h-10 rounded-xl border-2 border-line bg-white px-2.5 text-sm font-semibold text-ink focus:border-ink focus:outline-none";
const FIELD = `${FIELD_BASE} w-full`;

/** Structured edits only: lines, quantities, specs and a discount. There is deliberately no
 *  field for the total; the backend re-prices everything (D-009). */
export function EditDrawer({
  quote,
  catalog,
  busy,
  onClose,
  onSubmit,
}: {
  quote: QuoteDetail;
  catalog: CatalogOption[];
  busy: boolean;
  onClose: () => void;
  onSubmit: (decision: Decision) => void;
}) {
  const [lines, setLines] = useState<Line[]>(() =>
    quote.items.map((i, key) => ({ key, sku: i.sku, quantity: i.quantity, specs: { ...i.specs } })),
  );
  const [mode, setMode] = useState<DiscountMode>(quote.discount?.kind ?? "none");
  const [amount, setAmount] = useState<string>(() =>
    quote.discount ? String(quote.discount.value / 100) : "",
  );

  const bySku = Object.fromEntries(catalog.map((c) => [c.sku, c]));
  const update = (key: number, patch: Partial<Line>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const submit = () => {
    const value = Math.round(Number(amount) * 100); // ₹ → paise, or % → basis points
    const edits: Extract<Decision, { action: "edit" }>["edits"] = {
      items: lines.map((l) => ({ sku: l.sku, quantity: l.quantity, specs: l.specs })),
    };
    if (mode === "none") {
      if (quote.discount) edits.remove_discount = true;
    } else {
      edits.discount = { kind: mode, value };
    }
    onSubmit({ action: "edit", edits });
  };

  const invalid =
    lines.length === 0 ||
    lines.some((l) => !l.sku || !(l.quantity > 0)) ||
    (mode !== "none" && !(Number(amount) >= 0 && amount !== ""));

  return (
    <Modal title={`Edit ${quote.number} (creates revision ${quote.revision + 1})`} onClose={onClose} wide>
      <div className="flex flex-col gap-3.5">
        {lines.map((line) => {
          const item = bySku[line.sku];
          return (
            <div key={line.key} className="rounded-2xl border-2 border-line p-3.5">
              <div className="flex flex-wrap items-end gap-3">
                <label className={`min-w-[220px] flex-1 ${LABEL}`}>
                  Product
                  <select
                    value={line.sku}
                    onChange={(e) => update(line.key, { sku: e.target.value, specs: {} })}
                    className={FIELD}
                  >
                    {catalog.map((c) => (
                      <option key={c.sku} value={c.sku}>
                        {c.name} ({c.sku})
                      </option>
                    ))}
                  </select>
                </label>
                <label className={`w-36 ${LABEL}`}>
                  Quantity{item ? ` (${item.unit}, min ${item.moq})` : ""}
                  <input
                    type="number"
                    min={1}
                    value={line.quantity}
                    onChange={(e) => update(line.key, { quantity: Number(e.target.value) })}
                    className={`${FIELD} tabular-nums`}
                  />
                </label>
                <Button
                  variant="ghost"
                  onClick={() => setLines((ls) => ls.filter((l) => l.key !== line.key))}
                  disabled={lines.length === 1}
                >
                  Remove
                </Button>
              </div>
              {item && item.required_specs.length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-2.5 md:grid-cols-4">
                  {item.required_specs.map((spec) => {
                    const options = item.spec_options[spec];
                    const value = line.specs[spec] ?? "";
                    const set = (v: string) =>
                      update(line.key, { specs: { ...line.specs, [spec]: v } });
                    return (
                      <label key={spec} className={LABEL}>
                        {spec.replaceAll("_", " ")}
                        {options ? (
                          <select value={value} onChange={(e) => set(e.target.value)} className={FIELD}>
                            <option value="">choose…</option>
                            {options.map((o) => (
                              <option key={o} value={o}>
                                {o.replaceAll("_", " ")}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input value={value} onChange={(e) => set(e.target.value)} className={FIELD} />
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        <Button
          variant="secondary"
          className="self-start"
          onClick={() =>
            setLines((ls) => [
              ...ls,
              { key: Date.now(), sku: catalog[0]?.sku ?? "", quantity: catalog[0]?.moq ?? 1, specs: {} },
            ])
          }
        >
          <PlusIcon size={18} strokeWidth={2.4} />
          Add line
        </Button>

        <div className="flex flex-wrap items-end gap-3 rounded-2xl bg-mist p-3.5">
          <label className={LABEL}>
            Discount
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as DiscountMode)}
              className={FIELD_BASE}
            >
              <option value="none">No discount</option>
              <option value="flat">Flat amount (₹)</option>
              <option value="percent">Percent (%)</option>
            </select>
          </label>
          {mode !== "none" && (
            <label className={LABEL}>
              {mode === "flat" ? "Amount in ₹" : "Percent"}
              <input
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className={`${FIELD_BASE} w-32 tabular-nums`}
              />
            </label>
          )}
          <p className="min-w-[200px] flex-1 text-[13px] font-semibold text-ink-700">
            Discounts are applied before GST. The server recalculates every total.
          </p>
        </div>

        <div className="flex flex-wrap justify-end gap-2.5 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button size="lg" onClick={submit} disabled={busy || invalid}>
            {busy ? "Re-pricing…" : "Re-price as new revision"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
