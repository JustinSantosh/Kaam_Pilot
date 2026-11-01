# Phase 09: Business Ops console

- **Status:** Done
- **Depends on:** [08](phase-08.md)
- **Decisions:** [D-009](../decisions.md#d-009), [D-016](../decisions.md#d-016)

## Goal
The owner's workbench: see pending quotes, inspect exactly what the AI understood next to what the
code priced, edit, and approve or reject.

## Scope
**In:** inbox table, quote inspector, edit drawer, approve/reject actions, PDF preview, event history.
**Out:** analytics, multi-user roles.

## Deliverables
```
frontend/src/app/business/page.tsx
frontend/src/components/InboxTable.tsx     # status filter, sort by created_at
frontend/src/components/QuoteInspector.tsx # three panels (see below)
frontend/src/components/EditDrawer.tsx
frontend/src/components/PdfModal.tsx
frontend/src/components/EventTimeline.tsx
```

## Inspector layout
1. **Customer said:** raw message (and transcript for voice), customer notes received while pending.
2. **AI understood:** the `Extraction` (items, qty, specs), match confidence per item, any flags
   (unknown state, ambiguous match resolved).
3. **Priced by code:** line items, discount, tax rows, total, revision selector, PDF preview.
Actions: **Approve & send** · **Edit** · **Reject (reason)**.

## Tasks
- [x] Inbox polls every 3 s; badge count for `awaiting_approval`.
- [x] Edit drawer: change qty, swap SKU (catalog search), edit specs, add/remove line, discount
      (flat ₹ or %). Submits structured edits only ([D-009](../decisions.md#d-009)). No total field.
- [x] After edit, show the new revision and highlight the diff vs the previous revision.
- [x] Handle 409 (`stale_revision`, `quote_not_pending`) with a refresh prompt.
- [x] Confirmation dialog on Approve showing the final total.

## Exit criteria
- Demo: quote arrives in inbox → open → change qty 50→60 and 5% discount → revision 2 PDF with new
  totals → approve → Customer Hub shows the sent quote with PDF link.
- Reject with reason → customer gets a polite message; quote leaves the pending list.

## Risks / open questions
- `GET /api/catalog` endpoint needed for the SKU picker. Add it in Phase 07 if it's missing.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-09-ops-console`.
  - `/business`: inbox with filters (Needs review / Open / Closed / All) and a pending-count badge,
    polled every 3 s; selected quote polled every 5 s (so customer notes appear).
  - Quote inspector: header with status, revision, supply type and actions; flags (unknown state,
    money-override attempts); three panels: **Customer said** (raw text, delivery, messages received
    during review), **AI understood** (extracted items → matched SKU, specs, "calculated by code" notes
    such as derived sqft), **Priced by code** (lines, GST rate, discount, CGST/SGST or IGST, total,
    revision list); event history.
  - Edit drawer: change product, quantity, specs (option dropdowns from `/api/business/catalog`),
    add/remove lines, flat ₹ or % discount. No total field (D-009). Shows "total changed from X to Y"
    after re-pricing; `stale_revision` reloads the latest version.
  - Approve dialog shows the final total; reject requires a reason; PDF opens in a modal iframe.
  - Verified in the browser: edit 100→150 pcs + 5% discount gave revision 2 at ₹30,423.76 (checked
    by hand), then approve; the Customer Hub shows "Your quote KP-2026-0001 is ready." Lint, tsc and build pass.
