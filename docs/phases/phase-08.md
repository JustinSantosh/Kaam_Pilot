# Phase 08: Customer Hub (frontend)

- **Status:** Not started
- **Depends on:** [07](phase-07.md)
- **Decisions:** [D-005](../decisions.md#d-005), [D-016](../decisions.md#d-016)

## Goal
A Next.js app with a Customer Hub that simulates customers messaging the business, including ready-made
scenarios that show off the workflow in a demo.

## Scope
**In:** Next.js (App Router, TS) + Tailwind + shadcn/ui setup, layout with view switcher, typed API
client, Customer Hub page.
**Out:** Business Ops page (Phase 09), voice recording (Phase 10).

## Deliverables
```
frontend/package.json, tsconfig.json, tailwind config, components.json (shadcn)
frontend/src/app/layout.tsx           # header with Customer Hub / Business Ops switcher
frontend/src/app/customer/page.tsx
frontend/src/components/SessionSwitcher.tsx
frontend/src/components/ScenarioPresets.tsx
frontend/src/components/ChatStream.tsx
frontend/src/lib/api.ts               # typed client (types from OpenAPI or hand-written)
frontend/src/lib/money.ts             # formatPaise(1239000) → "₹12,390.00"
frontend/src/hooks/usePolling.ts
```

## Tasks
- [ ] Scaffold app; install shadcn components: button, input, card, badge, scroll-area, select.
- [ ] Session switcher: 3–4 fake customers (name, phone, state) stored in `localStorage`; each has its own `conversation_id`.
- [ ] Scenario presets (one click sends the message):
      complete apparel order · Hinglish incomplete order · multi-item fabrication · cancellation ·
      injection attempt · off-topic message.
- [ ] Chat stream: user bubbles, business replies, status chips (`Awaiting approval`, `Needs info`),
      PDF link card when a quote is sent.
- [ ] Poll `messages?since=` every 2–3 s while visible ([D-016](../decisions.md#d-016)).
- [ ] All money formatted by `formatPaise`; no arithmetic in the frontend ([D-005](../decisions.md#d-005)).

## Exit criteria
- Demo: pick customer → click "complete apparel order" → see "we're preparing your quote" and the
  `Awaiting approval` chip.
- Clarification scenario shows the exact question; replying completes it.
- `npm run build` and `npm run lint` pass.

## Risks / open questions
- Typed client: generate from OpenAPI (keeps types in sync) vs hand-written (fewer tools). Start with generated types.

## Notes / changelog
- 2026-10-31: phase file created.
