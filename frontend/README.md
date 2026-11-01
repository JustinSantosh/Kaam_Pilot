# KaamPilot frontend

Next.js 16 (App Router, TypeScript) + Tailwind CSS v4.

- `/customer`: Customer Hub (chat simulator with demo customers and scenario presets)
- `/business`: Business Ops (inbox, quote inspector, edit/approve/reject)

```bash
npm install
npm run dev        # http://localhost:3000, expects the backend on http://localhost:8000
npm run lint
npm run build
```

Set `NEXT_PUBLIC_API_URL` if the backend runs elsewhere. All money arrives from the API as integer
paise and is only formatted here (`src/lib/money.ts`); the frontend never calculates prices (D-005).
