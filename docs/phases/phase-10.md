# Phase 10: Guardrails & voice

- **Status:** Not started
- **Depends on:** [04](phase-04.md), [08](phase-08.md)
- **Decisions:** [D-002](../decisions.md#d-002), [D-015](../decisions.md#d-015)

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
- [ ] Rules + classifier + tests.
- [ ] Adversarial set (≥15): direct injection, injection hidden inside an order, system-prompt
      extraction, fake "owner says approve", Hinglish injection.
- [ ] Audio endpoint, transcription, `transcribe → guardrail` wiring.
- [ ] Customer Hub mic button (MediaRecorder → webm upload).

## Exit criteria
- Every adversarial case either ends in `reject_draft` **or** produces a quote whose money comes only
  from the catalog (assert no total deviates from deterministic pricing).
- False-positive check: the Phase 03 golden inquiries all pass the guardrail.
- A recorded Hinglish voice note produces a correct quote in the demo.

## Risks / open questions
- Whisper quality on noisy shop-floor audio: keep the transcript editable by the owner in a later iteration.

## Notes / changelog
- 2026-10-31: phase file created.
