# Phase 06: Quotation PDF

- **Status:** Done
- **Depends on:** [05](phase-05.md)
- **Decisions:** [D-005](../decisions.md#d-005), [D-006](../decisions.md#d-006), [D-012](../decisions.md#d-012), [D-021](../decisions.md#d-021)

## Goal
Replace the `render_pdf` stub with a professional quotation PDF generated from the priced quote, and
serve it safely.

## Scope
**In:** confirm/finalize [D-012](../decisions.md#d-012), Jinja2 template, renderer behind a
`render(quote) -> Path` interface, quote numbering, static file serving.
**Out:** sending the PDF to the customer (Phase 11), e-invoicing/IRN (out of MVP).

## Deliverables
```
backend/app/templates/quotation.html
backend/app/templates/quotation.css
backend/app/services/pdf.py          # render(quote_detail) -> Path
backend/app/services/numbering.py    # KP-YYYY-NNNN, sequential per year
backend/app/agent/nodes/render_pdf.py
backend/tests/test_pdf.py
```

## Template contents
Business header (name, GSTIN, address, logo from settings) · quote number + revision + date + validity ·
customer block (name, phone, state / place of supply) · line table (item, HSN, specs, qty, unit price,
setup fee, amount) · discount line · taxable value · CGST/SGST or IGST with rates · grand total in
figures **and words** (Indian numbering: lakh/crore) · terms (validity, advance %, delivery estimate) ·
footer "Draft. Not valid until approved" watermark on unapproved revisions.

## Tasks
- [x] Spike WeasyPrint on Windows (GTK) vs WSL/Docker; if too much friction, switch to ReportLab and
      update D-012 → Accepted / Superseded.
- [x] `render()` takes the **same** `PricedQuote` object stored in DB; no recalculation in the template.
- [x] Files saved as `storage/quotes/{quote_id}/r{revision}.pdf`.
- [x] Serve via `GET /files/quotes/{quote_id}/r{rev}.pdf` with path validation (no `..`), not a raw `StaticFiles` mount of `storage/`.
- [x] Amount-in-words helper with tests (₹12,39,000.50 → "Twelve Lakh Thirty-Nine Thousand Rupees and Fifty Paise").

## Exit criteria
- PDF generated for a 3-line quote; text extracted from the PDF (pypdf) contains the exact totals from DB.
- Intra-state and inter-state quotes show the right tax rows.
- Edit → revision 2 PDF exists and revision 1 is unchanged.
- Path traversal attempt returns 404.

## Risks / open questions
- Fonts with ₹ glyph and Devanagari (customer names): bundle Noto Sans + Noto Sans Devanagari.
- Pixel-level snapshot tests are brittle; prefer text extraction assertions.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-06-pdf`.
  - Spike result: WeasyPrint fails on Windows (no GTK). Switched to xhtml2pdf with the same Jinja2
    template ([D-021](../decisions.md#d-021), supersedes D-012). Amounts print as "Rs." (no ₹ glyph).
  - `render_pdf` node renders `quotes/{id}/r{rev}-draft.pdf` with a DRAFT mark; `dispatch` renders
    the final `r{rev}.pdf` on approval. Rendering runs in a worker thread.
  - Template: business header (`KP_BUSINESS_*` settings), quote number/revision/date/validity,
    customer, place of supply, lines with HSN and specs, discount, CGST/SGST or IGST rows,
    total in words (Indian numbering), terms, flags for the owner.
  - `GET /files/quotes/{quote_id}/r{n}[-draft].pdf`, strict name patterns (path traversal → 404).
  - Tests: 350 offline (15 new). PDF text is extracted with pypdf and checked against the stored totals.
