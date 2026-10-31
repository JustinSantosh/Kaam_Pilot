"use client";

import { useState } from "react";
import { fileUrl, type CatalogOption, type Decision, type QuoteDetail } from "@/lib/api";
import { formatPaise, formatRate } from "@/lib/money";
import { EditDrawer } from "./EditDrawer";
import { Modal } from "./Modal";
import { Button, Card, CardTitle, ErrorNote, StatusBadge } from "./ui";

const FLAG_TEXT: Record<string, string> = {
  customer_state_unknown_assumed_intra_state:
    "Customer's state is unknown. GST is shown as intra-state (CGST+SGST); confirm before sending.",
  guardrail_money_override:
    "The message tried to set a price or discount. It was ignored; prices come from the catalog.",
};

export function QuoteInspector({
  quote,
  catalog,
  busy,
  error,
  totalBeforeEdit,
  onDecide,
}: {
  quote: QuoteDetail;
  catalog: CatalogOption[];
  busy: boolean;
  error: string | null;
  totalBeforeEdit: number | null;
  onDecide: (decision: Decision) => Promise<boolean>;
}) {
  const [dialog, setDialog] = useState<"approve" | "reject" | "edit" | "pdf" | null>(null);
  const [reason, setReason] = useState("");
  const pending = quote.status === "awaiting_approval";
  const pdf = fileUrl(quote.pdf_url);

  const decide = async (decision: Decision) => {
    if (await onDecide(decision)) setDialog(null);
  };

  return (
    <div className="space-y-3">
      <Card>
        <div className="flex flex-wrap items-center gap-3 px-4 py-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-800">{quote.number}</h2>
              <StatusBadge status={quote.status} />
              <span className="text-xs text-slate-500">revision {quote.revision}</span>
            </div>
            <p className="text-xs text-slate-500">
              {quote.customer_name || "Customer"}
              {quote.customer_phone ? ` · ${quote.customer_phone}` : ""} ·{" "}
              {quote.supply_type === "inter_state" ? "Inter-state (IGST)" : "Intra-state (CGST+SGST)"}
              {quote.customer_state ? ` · ${quote.customer_state}` : ""}
            </p>
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            {pdf && (
              <Button variant="secondary" onClick={() => setDialog("pdf")}>
                View PDF
              </Button>
            )}
            {pending && (
              <>
                <Button variant="secondary" onClick={() => setDialog("edit")} disabled={busy}>
                  Edit
                </Button>
                <Button variant="danger" onClick={() => setDialog("reject")} disabled={busy}>
                  Reject
                </Button>
                <Button onClick={() => setDialog("approve")} disabled={busy}>
                  Approve &amp; send
                </Button>
              </>
            )}
          </div>
        </div>
        {totalBeforeEdit !== null && totalBeforeEdit !== quote.total_paise && (
          <div className="border-t border-slate-100 bg-brand-50 px-4 py-2 text-xs text-brand-700">
            Revision {quote.revision}: total changed from {formatPaise(totalBeforeEdit)} to{" "}
            <b>{formatPaise(quote.total_paise)}</b>.
          </div>
        )}
      </Card>

      <ErrorNote message={error} />
      {quote.edit_errors.map((e) => (
        <ErrorNote key={e} message={`Edit not applied: ${e}`} />
      ))}
      {quote.flags.map((f) => (
        <div
          key={f}
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
        >
          ⚠ {FLAG_TEXT[f] ?? f.replaceAll("_", " ")}
        </div>
      ))}

      <div className="grid gap-3 xl:grid-cols-[1fr_1fr_1.4fr]">
        <Card>
          <CardTitle>1 · Customer said</CardTitle>
          <div className="space-y-3 p-4 text-sm">
            <p className="whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-slate-700">
              {quote.raw_query}
            </p>
            {quote.extraction.delivery_by && (
              <p className="text-xs text-slate-500">Delivery: {quote.extraction.delivery_by}</p>
            )}
            {quote.customer_notes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-600">
                  Messages received during review
                </p>
                {quote.customer_notes.map((n, i) => (
                  <p key={i} className="mt-1 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
                    “{n}”
                  </p>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardTitle>2 · AI understood</CardTitle>
          <div className="space-y-3 p-4">
            {(quote.validation.items ?? []).map((item) => (
              <div key={item.index} className="rounded-md border border-slate-200 p-2.5 text-sm">
                <div className="flex justify-between gap-2">
                  <span className="font-medium text-slate-800">“{item.item_text}”</span>
                  <span className="text-xs text-slate-500">qty {item.quantity ?? "?"}</span>
                </div>
                <div className="mt-1 text-xs text-emerald-700">
                  → matched {item.name} ({item.sku})
                </div>
                <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-2 text-xs text-slate-600">
                  {Object.entries(item.specs).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-slate-400">{k.replaceAll("_", " ")}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
                {item.notes.map((n) => (
                  <p key={n} className="mt-1.5 rounded bg-sky-50 px-2 py-1 text-[11px] text-sky-800">
                    Calculated by code: {n}
                  </p>
                ))}
              </div>
            ))}
            <p className="text-[11px] text-slate-400">
              The LLM only fills this form. It has no fields for prices, tax or totals.
            </p>
          </div>
        </Card>

        <Card>
          <CardTitle>3 · Priced by code</CardTitle>
          <div className="p-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500">
                  <th className="pb-1 font-medium">Item</th>
                  <th className="pb-1 text-right font-medium">Qty</th>
                  <th className="pb-1 text-right font-medium">Rate</th>
                  <th className="pb-1 text-right font-medium">GST</th>
                  <th className="pb-1 text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {quote.items.map((l, i) => (
                  <tr key={i} className="align-top">
                    <td className="py-1.5 pr-2">
                      <div className="text-slate-800">{l.name}</div>
                      <div className="text-[11px] text-slate-400">
                        HSN {l.hsn}
                        {l.setup_fee_paise ? ` · setup ${formatPaise(l.setup_fee_paise)}` : ""}
                      </div>
                    </td>
                    <td className="py-1.5 text-right tabular-nums">
                      {l.quantity} {l.unit}
                    </td>
                    <td className="py-1.5 text-right tabular-nums">{formatPaise(l.unit_price_paise)}</td>
                    <td className="py-1.5 text-right tabular-nums">{formatRate(l.gst_rate_bp)}</td>
                    <td className="py-1.5 text-right tabular-nums">
                      {formatPaise(l.line_subtotal_paise)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <dl className="mt-3 space-y-1 border-t border-slate-200 pt-2 text-sm">
              <Row label="Subtotal" value={quote.totals.subtotal_paise} />
              {quote.totals.discount_paise > 0 && (
                <Row label="Discount" value={-quote.totals.discount_paise} />
              )}
              <Row label="Taxable value" value={quote.totals.taxable_paise} />
              {quote.supply_type === "inter_state" ? (
                <Row label="IGST" value={quote.totals.igst_paise} />
              ) : (
                <>
                  <Row label="CGST" value={quote.totals.cgst_paise} />
                  <Row label="SGST" value={quote.totals.sgst_paise} />
                </>
              )}
              <div className="flex justify-between border-t border-slate-200 pt-1.5 text-base font-semibold">
                <dt>Total</dt>
                <dd className="tabular-nums">{formatPaise(quote.totals.total_paise)}</dd>
              </div>
            </dl>
            {quote.revisions.length > 1 && (
              <p className="mt-2 text-[11px] text-slate-400">
                Revisions: {quote.revisions.map((r) => `R${r}`).join(", ")}. All are kept for audit.
              </p>
            )}
            {quote.rejection_reason && (
              <p className="mt-2 text-xs text-red-700">Rejected: {quote.rejection_reason}</p>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>History</CardTitle>
        <ol className="space-y-1 p-4 text-xs text-slate-600">
          {quote.events.map((e, i) => (
            <li key={i} className="flex gap-3">
              <span className="w-16 shrink-0 tabular-nums text-slate-400">
                {new Date(e.created_at.endsWith("Z") ? e.created_at : `${e.created_at}Z`).toLocaleTimeString(
                  [],
                  { hour: "2-digit", minute: "2-digit" },
                )}
              </span>
              <span>{e.kind.replace("status:", "→ ").replaceAll("_", " ")}</span>
            </li>
          ))}
        </ol>
      </Card>

      {dialog === "approve" && (
        <Modal title="Approve and send this quote?" onClose={() => setDialog(null)}>
          <p className="text-sm text-slate-700">
            {quote.customer_name || "The customer"} will receive {quote.number} (revision{" "}
            {quote.revision}) with a total of <b>{formatPaise(quote.total_paise)}</b>, and a
            follow-up is scheduled.
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button disabled={busy} onClick={() => decide({ action: "approve" })}>
              {busy ? "Sending…" : "Approve & send"}
            </Button>
          </div>
        </Modal>
      )}

      {dialog === "reject" && (
        <Modal title="Reject this quote" onClose={() => setDialog(null)}>
          <label className="text-xs text-slate-500">
            Reason (kept for your records)
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="mt-1 block w-full rounded border border-slate-300 px-2 py-1.5 text-sm text-slate-800"
              placeholder="e.g. Out of stock until December"
            />
          </label>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={busy || !reason.trim()}
              onClick={() => decide({ action: "reject", reason: reason.trim() })}
            >
              Reject
            </Button>
          </div>
        </Modal>
      )}

      {dialog === "edit" && (
        <EditDrawer
          quote={quote}
          catalog={catalog}
          busy={busy}
          onClose={() => setDialog(null)}
          onSubmit={(d) => void decide(d)}
        />
      )}

      {dialog === "pdf" && pdf && (
        <Modal title={`${quote.number} · revision ${quote.revision}`} onClose={() => setDialog(null)} wide>
          <iframe src={pdf} title="Quotation PDF" className="h-[75vh] w-full rounded border" />
          <a href={pdf} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-brand-600">
            Open in a new tab
          </a>
        </Modal>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between text-slate-600">
      <dt>{label}</dt>
      <dd className="tabular-nums">{formatPaise(value)}</dd>
    </div>
  );
}
