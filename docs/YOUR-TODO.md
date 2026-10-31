# Your to-do list

Everything that can be built and tested without your accounts or your decisions is done. This list is
what's left for **you**, in the order I'd do it. Each item says why it matters and how to check it worked.

---

## 1. Get the code onto `main` (do this first)

Each phase is on its own branch, and **each branch is built on top of the previous one**:

```
main ← phase-03-extraction ← phase-04-graph ← phase-05-hitl ← phase-06-pdf ← phase-07-api
     ← phase-08-customer-hub ← phase-09-ops-console ← phase-10-guardrails-voice
     ← phase-11-dispatch ← phase-12-evals ← phase-13-hardening
```

Plus one small, independent branch: `docs/coderabbit-manual-trigger`.

**Option A (recommended, reviewed by CodeRabbit phase by phase):**
1. Open a PR from `phase-03-extraction` into `main`:
   https://github.com/JustinSantosh/Kaam_Pilot/compare/main...phase-03-extraction
2. Comment `@coderabbitai review` (reviews are manual on repos under 10 stars).
3. Merge it with **"Create a merge commit"**. Don't use squash or rebase: they rewrite commits, and the
   next branches would then show conflicts.
4. Repeat for `phase-04-graph`, `phase-05-hitl`, … `phase-13-hardening`, in order. Each PR now shows
   only that phase's changes.

**Option B (fastest):** one PR from `phase-13-hardening` into `main` contains everything.

Also merge or close `docs/coderabbit-manual-trigger`, and delete the already-merged
`chore/readme-status` branch on GitHub.

✅ *Check:* the **CI** workflow (GitHub → Actions) passes on the PR. It runs lint, 418 tests, the eval
gate and the frontend build. It has passed locally, but this will be its first run on GitHub.

---

## 2. Turn on the real LLM (Gemini)

The app runs today in **demo mode** (`KP_LLM_MODEL=demo`), which only understands the preset
scenarios well. For real messages:

1. Get a key from Google AI Studio.
2. Edit `backend/.env` yourself (it's gitignored, so never paste the key into chat or commit it):
   ```
   KP_LLM_MODEL=google_genai:gemini-3.5-flash-lite
   GOOGLE_API_KEY=your-key
   ```
3. Run the live checks:
   ```bash
   cd backend
   .venv/Scripts/python -m pytest -m llm -v
   .venv/Scripts/python -m evals.run_evals --mode live --record
   ```
4. Share the report from `backend/evals/reports/` with me (or read it yourself). Then:
   - mark [D-020](decisions.md#d-020) Accepted, or switch to `gemini-3.6-flash` if accuracy is poor,
     and re-run `--mode live --record` with that model to compare;
   - put the live numbers in the README's "Eval results" table and in `pitch.md`;
   - fix the top failure patterns (prompt wording, catalog aliases, matcher thresholds) and re-run.
     This is the "error analysis" task still open in Phase 12.

✅ *Check:* `pytest -m llm` shows at least 9/10 golden inquiries passing (Phase 03 exit criterion).

**Not verified yet (needs the key):** Gemini voice-note transcription (Phase 10). After step 2,
record a Hinglish voice note with the 🎤 button in the Customer Hub and confirm the quote is right.

---

## 3. Put in your real business details

Add to `backend/.env`. These print on every PDF:

```
KP_BUSINESS_NAME=Sharma Prints & Fabrication
KP_BUSINESS_GSTIN=22ABCDE1234F1Z5
KP_BUSINESS_ADDRESS=Main Road, Raipur, Chhattisgarh
KP_BUSINESS_PHONE=+91 98000 00000
KP_BUSINESS_STATE=CG              # decides CGST+SGST vs IGST
KP_QUOTE_VALIDITY_DAYS=15
KP_ADVANCE_PERCENT=50
```

---

## 4. Replace the seed catalog with your real one ⚠️

`backend/app/data/catalog.json` has 10 **example** products. Prices, HSN codes and GST rates in it are
illustrative. Replace them with your real items: name, nicknames customers use ("kaali tee",
"almari"), price tiers, MOQ, setup fee, required details, option surcharges, HSN code and GST rule.
The app refuses to start if the catalog is invalid, and the error says what's wrong.

**Ask your accountant these three questions** (the code works either way; the answers can change totals by paise):
1. Should GST be rounded **per line** (current) or once on the whole quote?
2. Is the **setup fee** taxed at the item's GST rate (current assumption)?
3. For price-slab GST (apparel), should the setup fee count toward the **per-piece value** (it does now)?

After changing the catalog, rebuild the eval dataset and review what changed:
```bash
cd backend && .venv/Scripts/python -m evals.build_dataset
```

---

## 5. Small setup items

- **Git name:** commits so far used `JustinSantosh` only for those commits. To set it permanently:
  `git config --global user.name "JustinSantosh"`
- **Tracing (optional):** add `LANGSMITH_API_KEY=…` and `LANGSMITH_TRACING=true` to `backend/.env` to
  see every graph run and LLM call in LangSmith (labelled by conversation and prompt version).
- **Docker (optional):** Docker isn't installed on this machine, so the Dockerfiles and compose file
  were written but **never built**. Install Docker Desktop, run `docker compose up --build`, and tell me
  if anything fails.
- **Demo follow-ups:** set `KP_FOLLOWUP_HOURS=0.01` before a live demo so the follow-up fires in ~36 s.

---

## 6. Before anyone outside can use it

- The Business Ops console has **no login**. Don't deploy it on a public URL as-is; adding auth is the
  first production task.
- Set `KP_CORS_ORIGINS` (backend) and `NEXT_PUBLIC_API_URL` (frontend build) to your real domains if you deploy.
- Keep `uvicorn --workers 1` (one follow-up scheduler per process, D-013).

---

## 7. Nice-to-have next steps (not started)

- Real **WhatsApp Business** channel: implement the `Outbound` protocol in `app/services/outbound.py`.
- **₹ symbol in PDFs:** bundle a font such as Noto Sans and register it in the template (PDFs print "Rs." today).
- Postgres instead of SQLite when you have more than one shop (checkpointer + records DB).
- An editable transcript for voice notes in the inspector.
