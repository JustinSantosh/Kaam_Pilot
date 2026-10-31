# Phase 10: Guardrails & voice

- **Status:** Done (live voice check pending API key)
- **Depends on:** [04](phase-04.md), [08](phase-08.md)
- **Decisions:** [D-002](../decisions.md#d-002), [D-015](../decisions.md#d-015), [D-024](../decisions.md#d-024)

## Goal
Handle hostile and off-topic input gracefully, and accept voice notes (including Hinglish) as input.

## Scope
**In:** real `guardrail` node (rules + small classifier), `reject_draft` replies, `transcribe` node,
audio upload endpoint, mic recording in Customer Hub, adversarial test set.
**Out:** content moderation beyond the business domain, speaker identification.

## Deliverables
```
backend/app/services/guardrail.py     # rule checks + classify_risk()
backend/app/llm/prompts/guardrail_v1.md
backend/app/agent/nodes/guardrail.py
backend/app/agent/nodes/transcribe.py
backend/app/services/transcribe.py    # Whisper (or compatible) wrapper
backend/app/api/routes_chat.py        # + POST /api/chat/send-audio (multipart)
frontend/src/components/VoiceRecorder.tsx
backend/tests/test_guardrail.py
backend/tests/adversarial/cases.json
```

## Design
- Layers per [D-015](../decisions.md#d-015): architecture first, then the guardrail.
- **Rules (cheap, run first):** max length, prompt-leak patterns ("system prompt", "ignore previous"),
  money-override patterns ("price 0", "100% discount"). A rule hit flags but does **not** auto-block
  money-override phrasing; the order may still be real. Instead, add a visible flag for the owner.
- **Classifier:** `{risk: none|injection|abuse|off_topic, reason}`. Only `injection` / `abuse` route to
  `reject_draft`. `off_topic` goes to `reply_draft`.
- **Voice:** audio ≤ 2 min, stored under `storage/audio/`, transcript saved on the conversation and
  shown in the inspector. Use a prompt hint listing catalog terms to help with jargon and Hinglish.

## Tasks
- [x] Rules + classifier + tests.
- [x] Adversarial set (≥15): direct injection, injection hidden inside an order, system-prompt
      extraction, fake "owner says approve", Hinglish injection.
- [x] Audio endpoint, transcription, `transcribe → guardrail` wiring.
- [x] Customer Hub mic button (MediaRecorder → webm upload).

## Exit criteria
- Every adversarial case either ends in `reject_draft` **or** produces a quote whose money comes only
  from the catalog (assert no total deviates from deterministic pricing).
- False-positive check: the Phase 03 golden inquiries all pass the guardrail.
- A recorded Hinglish voice note produces a correct quote in the demo.

## Risks / open questions
- Whisper quality on noisy shop-floor audio: keep the transcript editable by the owner in a later iteration.

## Notes / changelog
- 2026-10-31: phase file created.
- 2026-11-01: implemented on branch `phase-10-guardrails-voice`.
  - `services/guardrail.py`: injection rules (ignore instructions, system prompt, admin/developer
    mode, tag smuggling, jailbreak…) refuse without spending an LLM call; money-override phrases
    ("make the price 0", "100% discount", "free of cost") don't block a genuine order but add the
    `guardrail_money_override` flag to the quote for the owner. Then the optional LLM risk check
    (`guardrail_v1` prompt): `injection`/`abuse` → `reject_draft`; it **fails open** on errors (D-015).
  - Graph: `guardrail → reject_draft → END` (polite refusal, nothing extracted or priced).
  - Voice: `POST /api/chat/send-audio`, transcribed before the graph ([D-024](../decisions.md#d-024));
    frontend mic button (MediaRecorder, max 120 s).
  - Adversarial set `tests/adversarial/cases.json` (18 cases): 9 refused by rules, 2 by the LLM check,
    4 orders with money-override text that are quoted at exact catalog prices and flagged, 3 benign ones
    that aren't refused. All golden inquiries pass with no false positives.
  - Verified in the browser: the injection preset gets the refusal and no quote is created.
  - Not verified: real Gemini audio transcription (needs the API key).
  - Tests: 398 offline (32 new).
