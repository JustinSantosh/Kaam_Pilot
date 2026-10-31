# KaamPilot

A human-in-the-loop quotation workflow for custom service and trade businesses (apparel printing,
fabrication, carpentry, interior contracting). It reads messy text, Hinglish or voice inquiries,
prices them with deterministic code, drafts a PDF quote, and waits for the owner's approval
before anything reaches the customer.

**The LLM reads. Code calculates. The owner approves.**

- [Project spec](docs/project.md): what it is, architecture, data model, API, phase index
- [Decision log](docs/decisions.md): every design decision, why it matters, and why not the alternatives
- [Phases](docs/phases/): the phase-by-phase implementation plan (`phase-01.md` … `phase-13.md`)
- [Development workflow](docs/project.md#11-development-workflow): one branch + PR per phase,
  reviewed by CodeRabbit on every pushed commit

## Status

| Phase | Status |
|---|---|
| 01 Foundations & project docs | Done |
| 02 Catalog & deterministic pricing | Done |
| 03–13 | Not started; see the [phase index](docs/project.md#8-phase-index) |
