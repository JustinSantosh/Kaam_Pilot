"use client";

import { useState, type ReactNode } from "react";
import { fileUrl, type CatalogOption, type Decision, type QuoteDetail } from "@/lib/api";
import { formatPaise, formatRate } from "@/lib/money";
import { EditDrawer } from "./EditDrawer";
import { AlertIcon, CheckIcon, CloseIcon, FileIcon, PencilIcon, SendIcon } from "./icons";
import { Modal } from "./Modal";
import { Button, ErrorNote, StatusBadge } from "./ui";

const FLAG_TEXT: Record<string, string> = {
  customer_state_unknown_assumed_intra_state:
    "Customer's state is unknown. GST is shown as intra-state (CGST+SGST); confirm before sending.",
  guardrail_money_override:
    "The message tried to set a price or discount. It was ignored; prices come from the catalog.",
};

const EVENT_TEXT: Record<string, string> = {
  created: "Quote created",
  priced: "Priced by code",
  edited: "Edited by the owner",
  edit_rejected: "Edit not applied",
  customer_note: "Customer messaged during review",
  followup_scheduled: "Follow-up scheduled",
  followup_cancelled: "Follow-up cancelled",
  "status:awaiting_approval": "Waiting for your OK",
  "status:approved": "Approved",
  "status:sent": "Sent to the customer",
  "status:followed_up": "Follow-up nudge sent",
  "status:accepted": "Accepted by the customer",
  "status:rejected": "Rejected",
  "status:cancelled": "Cancelled by the customer",
  "status:lapsed": "Lapsed",
};

const eventText = (kind: string) =>
  EVENT_TEXT[kind] ?? kind.replace("status:", "→ ").replaceAll("_", " ");

const clock = (iso: string) =>
  new Date(iso.endsWith("Z") ? iso : `${iso}Z`).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

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
  const interState = quote.supply_type === "inter_state";
  const firstName = quote.customer_name ? quote.customer_name.split(/\s+/)[0] : "the customer";

  const decide = async (decision: Decision) => {
    if (await onDecide(decision)) setDialog(null);
  };

  return (
    <div className="flex flex-col gap-4">
      <section
        aria-labelledby="quote-title"
        className="flex flex-wrap items-center gap-x-6 gap-y-4 rounded-3xl border-2 border-ink bg-white px-5 py-5 shadow-pop-lg sm:px-6"
      >
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 id="quote-title" className="font-display text-[30px] font-extrabold leading-tight tracking-[-0.03em]">
              {quote.number}
            </h2>
            <StatusBadge status={quote.status} />
            <span className="text-sm font-bold text-ink-500">Revision {quote.revision}</span>
          </div>
          <p className="text-[15px] leading-normal text-ink-700">
            {quote.customer_name || "Customer"}
            {quote.customer_phone ? ` · ${quote.customer_phone}` : ""} ·{" "}
            {interState ? "Inter-state (IGST)" : "Intra-state (CGST + SGST)"}
            {quote.customer_state ? ` · ${quote.customer_state}` : ""}
          </p>
        </div>
        <div className="ml-auto flex flex-col items-end gap-0.5">
          <span className="text-xs font-extrabold uppercase tracking-[0.1em] text-ink-500">Total incl. GST</span>
          <span className="font-display text-[34px] font-extrabold leading-tight tracking-[-0.03em] tabular-nums">
            {formatPaise(quote.total_paise)}
          </span>
        </div>
        {(pdf || pending) && (
          <div className="flex basis-full flex-wrap gap-2.5 border-t-2 border-dashed border-line pt-4">
            {pdf && (
              <Button variant="secondary" onClick={() => setDialog("pdf")}>
                <FileIcon size={18} />
                View PDF
              </Button>
            )}
            {pending && (
              <>
                <Button variant="secondary" onClick={() => setDialog("edit")} disabled={busy}>
                  <PencilIcon size={18} />
                  Edit
                </Button>
                <Button variant="danger" onClick={() => setDialog("reject")} disabled={busy}>
                  <CloseIcon size={18} strokeWidth={2.2} />
                  Reject
                </Button>
                <Button size="lg" onClick={() => setDialog("approve")} disabled={busy} className="ml-auto">
                  <SendIcon size={20} />
                  Approve &amp; send
                </Button>
              </>
            )}
          </div>
        )}
        {totalBeforeEdit !== null && totalBeforeEdit !== quote.total_paise && (
          <p className="basis-full rounded-2xl bg-marigold-soft px-4 py-2.5 text-sm font-semibold">
            Revision {quote.revision}: total changed from {formatPaise(totalBeforeEdit)} to{" "}
            <b>{formatPaise(quote.total_paise)}</b>.
          </p>
        )}
      </section>

      <ErrorNote message={error} />
      {quote.edit_errors.map((e) => (
        <ErrorNote key={e} message={`Edit not applied: ${e}`} />
      ))}
      {quote.flags.map((f) => (
        <div
          key={f}
          className="flex items-start gap-2.5 rounded-2xl border-2 border-ink bg-marigold-soft px-3.5 py-2.5 text-sm font-semibold"
        >
          <AlertIcon size={18} className="mt-px shrink-0" />
          <span>{FLAG_TEXT[f] ?? f.replaceAll("_", " ")}</span>
        </div>
      ))}

      <div className="flex flex-wrap items-stretch gap-4">
        <Panel n={1} title="Customer said" tone="bg-rani-soft" badge="bg-rani-pop" className="flex-[1_1_240px]">
          <p className="whitespace-pre-wrap rounded-[18px] rounded-bl-md border-[1.5px] border-line bg-mist px-3.5 py-3 text-[15px] leading-relaxed">
            {quote.raw_query}
          </p>
          {quote.extraction.delivery_by && (
            <p className="text-[13px] font-semibold text-ink-500">Delivery: {quote.extraction.delivery_by}</p>
          )}
          {quote.customer_notes.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-[13px] font-extrabold text-ink-700">Messages received during review</p>
              {quote.customer_notes.map((n, i) => (
                <p key={i} className="rounded-xl bg-marigold-soft px-3 py-1.5 text-[13px]">
                  “{n}”
                </p>
              ))}
            </div>
          )}
        </Panel>

        <Panel n={2} title="AI understood" tone="bg-peacock-soft" badge="bg-peacock-pop" className="flex-[1_1_240px]">
          {(quote.validation.items ?? []).map((item) => (
            <div key={item.index} className="flex flex-col gap-2 rounded-2xl border-[1.5px] border-line px-3.5 py-3">
              <span className="flex items-baseline justify-between gap-2">
                <span className="text-[15px] font-extrabold">“{item.item_text}”</span>
                <span className="shrink-0 text-[13px] font-bold text-ink-500">qty {item.quantity ?? "?"}</span>
              </span>
              {item.sku ? (
                <span className="flex items-start gap-1.5 text-[13px] font-bold text-leaf-700">
                  <CheckIcon size={14} strokeWidth={2.8} className="mt-0.5 shrink-0" />
                  {item.name} · {item.sku}
                </span>
              ) : (
                <span className="flex items-start gap-1.5 text-[13px] font-bold text-chilli">
                  <AlertIcon size={14} className="mt-0.5 shrink-0" />
                  No catalogue match
                </span>
              )}
              {Object.keys(item.specs).length > 0 && (
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[13px]">
                  {Object.entries(item.specs).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-ink-500">{k.replaceAll("_", " ")}</dt>
                      <dd className="font-semibold">{v}</dd>
                    </div>
                  ))}
                </dl>
              )}
              {item.notes.map((n) => (
                <p key={n} className="rounded-lg bg-peacock-soft px-2.5 py-1 text-xs font-semibold text-peacock-700">
                  Calculated by code: {n}
                </p>
              ))}
            </div>
          ))}
          <p className="mt-auto text-xs leading-normal text-ink-500">
            The model only fills this form. It has no fields for prices, tax or totals.
          </p>
        </Panel>

        <Panel n={3} title="Priced by code" tone="bg-marigold-soft" badge="bg-marigold" className="flex-[1.4_1_380px]">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[360px] border-collapse text-sm tabular-nums">
              <thead>
                <tr className="text-xs uppercase tracking-[0.08em] text-ink-500">
                  <th className="pb-2 pr-2 text-left font-extrabold">Item</th>
                  <th className="pb-2 pl-2 text-right font-extrabold">Qty</th>
                  <th className="pb-2 pl-2 text-right font-extrabold">Rate</th>
                  <th className="pb-2 pl-2 text-right font-extrabold">GST</th>
                  <th className="pb-2 pl-2 text-right font-extrabold">Amount</th>
                </tr>
              </thead>
              <tbody>
                {quote.items.map((l, i) => (
                  <tr key={i} className="border-t-[1.5px] border-line align-top">
                    <td className="py-2.5 pr-2">
                      <span className="block font-bold">{l.name}</span>
                      <span className="mt-0.5 block text-xs text-ink-500">
                        HSN {l.hsn}
                        {l.setup_fee_paise ? ` · setup ${formatPaise(l.setup_fee_paise)}` : ""}
                      </span>
                    </td>
                    <td className="whitespace-nowrap py-2.5 pl-2 text-right">
                      {l.quantity} {l.unit}
                    </td>
                    <td className="py-2.5 pl-2 text-right">{formatPaise(l.unit_price_paise)}</td>
                    <td className="py-2.5 pl-2 text-right">{formatRate(l.gst_rate_bp)}</td>
                    <td className="py-2.5 pl-2 text-right font-extrabold">{formatPaise(l.line_subtotal_paise)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <dl className="flex flex-col gap-1.5 border-t-2 border-ink pt-3 text-sm">
            <Row label="Subtotal" value={quote.totals.subtotal_paise} />
            {quote.totals.discount_paise > 0 && <Row label="Discount" value={-quote.totals.discount_paise} />}
            <Row label="Taxable value" value={quote.totals.taxable_paise} />
            {interState ? (
              <Row label="IGST" value={quote.totals.igst_paise} />
            ) : (
              <>
                <Row label="CGST" value={quote.totals.cgst_paise} />
                <Row label="SGST" value={quote.totals.sgst_paise} />
              </>
            )}
            <div className="mt-1.5 flex items-baseline justify-between gap-3 rounded-[14px] border-2 border-ink bg-marigold px-3.5 py-2.5">
              <dt className="text-[15px] font-extrabold">Total</dt>
              <dd className="font-display text-2xl font-extrabold tracking-[-0.02em] tabular-nums">
                {formatPaise(quote.totals.total_paise)}
              </dd>
            </div>
          </dl>
          {quote.revisions.length > 1 && (
            <p className="text-xs text-ink-500">
              Revisions: {quote.revisions.map((r) => `R${r}`).join(", ")}. All are kept for audit.
            </p>
          )}
          {quote.rejection_reason && (
            <p className="text-[13px] font-semibold text-chilli">Rejected: {quote.rejection_reason}</p>
          )}
        </Panel>
      </div>

      <section aria-labelledby="log-title" className="rounded-[22px] border-2 border-ink bg-white px-5 py-4">
        <h3 id="log-title" className="font-display text-lg font-extrabold tracking-[-0.01em]">
          Flight log
        </h3>
        <ol className="mt-3 flex flex-col">
          {quote.events.map((e, i) => {
            const last = i === quote.events.length - 1;
            return (
              <li key={i} className="flex gap-3">
                <span className="w-[4.5rem] shrink-0 whitespace-nowrap text-[13px] font-bold tabular-nums text-ink-500">
                  {clock(e.created_at)}
                </span>
                <span className="flex flex-col items-center">
                  <span
                    className={`mt-0.5 size-3.5 shrink-0 rounded-full border-2 border-ink ${
                      e.kind.startsWith("status:") ? "bg-marigold" : "bg-white"
                    }`}
                  />
                  {!last && <span className="w-0 flex-1 border-l-2 border-dashed border-ink" />}
                </span>
                <span className={`text-sm font-semibold ${last ? "" : "pb-3"}`}>{eventText(e.kind)}</span>
              </li>
            );
          })}
        </ol>
      </section>

      {dialog === "approve" && (
        <Modal title={`Sab sahi? Send it to ${firstName}.`} onClose={() => setDialog(null)}>
          <p className="text-[15px] leading-relaxed text-ink-700">
            {quote.customer_name || "The customer"} gets {quote.number} (revision {quote.revision}) in the chat,
            with the PDF. A follow-up is scheduled in case there&apos;s no reply.
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-[18px] border-2 border-ink bg-mist px-4 py-3.5">
            <span className="flex flex-col gap-0.5">
              <span className="text-xs font-extrabold uppercase tracking-[0.1em] text-ink-500">Total incl. GST</span>
              <span className="font-display text-[30px] font-extrabold leading-tight tracking-[-0.03em] tabular-nums">
                {formatPaise(quote.total_paise)}
              </span>
            </span>
            <span className="text-right text-sm font-bold text-ink-700">
              {quote.items.length} line{quote.items.length === 1 ? "" : "s"} ·{" "}
              {interState ? "IGST" : "CGST + SGST"}
            </span>
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-2.5">
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Not yet
            </Button>
            <Button size="lg" disabled={busy} onClick={() => decide({ action: "approve" })}>
              <SendIcon size={20} />
              {busy ? "Sending…" : "Approve & send"}
            </Button>
          </div>
        </Modal>
      )}

      {dialog === "reject" && (
        <Modal title="Reject this quote" onClose={() => setDialog(null)}>
          <label className="block text-sm font-extrabold text-ink-700">
            Reason (kept for your records)
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="mt-1.5 block w-full rounded-[14px] border-2 border-line bg-mist px-3 py-2.5 text-[15px] font-normal text-ink focus:border-ink focus:outline-none"
              placeholder="e.g. Out of stock until December"
            />
          </label>
          <div className="mt-5 flex flex-wrap justify-end gap-2.5">
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={busy || !reason.trim()}
              onClick={() => decide({ action: "reject", reason: reason.trim() })}
            >
              <CloseIcon size={18} strokeWidth={2.2} />
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
          <iframe src={pdf} title="Quotation PDF" className="h-[75vh] w-full rounded-2xl border-2 border-ink" />
          <a
            href={pdf}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex min-h-11 items-center text-sm font-extrabold text-rani hover:underline"
          >
            Open in a new tab
          </a>
        </Modal>
      )}
    </div>
  );
}

function Panel({
  n,
  title,
  tone,
  badge,
  className,
  children,
}: {
  n: number;
  title: string;
  tone: string;
  badge: string;
  className: string;
  children: ReactNode;
}) {
  return (
    <section className={`flex min-w-0 flex-col overflow-hidden rounded-[22px] border-2 border-ink bg-white ${className}`}>
      <h3
        className={`flex items-center gap-2.5 border-b-2 border-ink px-4 py-3 font-display text-lg font-extrabold tracking-[-0.01em] ${tone}`}
      >
        <span
          className={`flex size-7.5 shrink-0 items-center justify-center rounded-full border-2 border-ink text-[15px] ${badge}`}
        >
          {n}
        </span>
        {title}
      </h3>
      <div className="flex flex-1 flex-col gap-3 p-4">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between gap-3 text-ink-700">
      <dt>{label}</dt>
      <dd className="tabular-nums">{formatPaise(value)}</dd>
    </div>
  );
}
