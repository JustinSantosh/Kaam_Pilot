"use client";

import { useState } from "react";
import type { CatalogOption, Decision, QuoteDetail } from "@/lib/api";
import { Modal } from "./Modal";
import { Button } from "./ui";

interface Line {
  key: number;
  sku: string;
  quantity: number;
  specs: Record<string, string>;
}

type DiscountMode = "none" | "flat" | "percent";

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
      <div className="space-y-3">
        {lines.map((line) => {
          const item = bySku[line.sku];
          return (
            <div key={line.key} className="rounded-md border border-slate-200 p-3">
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex-1 text-xs text-slate-500">
                  Product
                  <select
                    value={line.sku}
                    onChange={(e) => update(line.key, { sku: e.target.value, specs: {} })}
                    className="mt-1 block w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-800"
                  >
                    {catalog.map((c) => (
                      <option key={c.sku} value={c.sku}>
                        {c.name} ({c.sku})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="w-32 text-xs text-slate-500">
                  Quantity{item ? ` (${item.unit}, min ${item.moq})` : ""}
                  <input
                    type="number"
                    min={1}
                    value={line.quantity}
                    onChange={(e) => update(line.key, { quantity: Number(e.target.value) })}
                    className="mt-1 block w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-800"
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
                <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
                  {item.required_specs.map((spec) => {
                    const options = item.spec_options[spec];
                    const value = line.specs[spec] ?? "";
                    const set = (v: string) =>
                      update(line.key, { specs: { ...line.specs, [spec]: v } });
                    return (
                      <label key={spec} className="text-xs text-slate-500">
                        {spec.replaceAll("_", " ")}
                        {options ? (
                          <select
                            value={value}
                            onChange={(e) => set(e.target.value)}
                            className="mt-1 block w-full rounded border border-slate-300 px-2 py-1 text-sm text-slate-800"
                          >
                            <option value="">choose…</option>
                            {options.map((o) => (
                              <option key={o} value={o}>
                                {o.replaceAll("_", " ")}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            value={value}
                            onChange={(e) => set(e.target.value)}
                            className="mt-1 block w-full rounded border border-slate-300 px-2 py-1 text-sm text-slate-800"
                          />
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
          onClick={() =>
            setLines((ls) => [
              ...ls,
              { key: Date.now(), sku: catalog[0]?.sku ?? "", quantity: catalog[0]?.moq ?? 1, specs: {} },
            ])
          }
        >
          + Add line
        </Button>

        <div className="flex flex-wrap items-end gap-3 rounded-md bg-slate-50 p-3">
          <label className="text-xs text-slate-500">
            Discount
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as DiscountMode)}
              className="mt-1 block rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-800"
            >
              <option value="none">No discount</option>
              <option value="flat">Flat amount (₹)</option>
              <option value="percent">Percent (%)</option>
            </select>
          </label>
          {mode !== "none" && (
            <label className="text-xs text-slate-500">
              {mode === "flat" ? "Amount in ₹" : "Percent"}
              <input
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="mt-1 block w-32 rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-800"
              />
            </label>
          )}
          <p className="text-xs text-slate-500">
            Discounts are applied before GST. Totals are recalculated by the server.
          </p>
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy || invalid}>
            {busy ? "Re-pricing…" : "Re-price as new revision"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
