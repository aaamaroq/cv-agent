# ADR 0006: Keep the loaded rewrite as the stored history

- **Status:** Accepted
- **Date:** 2026-10-15

## Context

When the input guardrail classifies a message as `loaded` — a real question
wrapped in hostility, insults or leading rhetoric — it emits a neutral rewrite
(`neutral_question`) and the chatbot node builds
`rewrite = HumanMessage(content=state["neutral_question"], id=last_human.id)`.
Reusing the original message id means the neutral rewrite **replaces** the
hostile original in the checkpoint history: it is not appended alongside it.

This is a real semantic choice about what a thread remembers. The model never
sees the raw hostility again on later turns — neither does any consumer reading
the checkpoint — so the provenance of the original wording is intentionally
lost. History stays consistent with what the assistant actually answered: the
neutral question it replied to.

## Decision

Keep the current replacement behavior. A `loaded` question is rewritten in
place (same message id), the neutral wording becomes the thread's history, and
the original hostile wording is not retained anywhere. The document that the
provenance loss is intentional — not an oversight — so a future reader does not
"fix" it by resurrecting the hostile text into context.

## Consequences

- Later turns cannot reintroduce the hostile framing into the model's context,
  because the raw wording is gone from the checkpoint. Follow-ups build on the
  neutral question the assistant actually answered.
- History is self-consistent: what is stored is exactly what the assistant was
  asked, so transcripts read coherently end to end.
- Provenance of the original hostile wording is permanently lost by design;
  there is no way to audit what was actually said after the fact.
- Ergonomic consequence for any future `GET /api/history` feature: the stored
  message **is** the neutral question. Clients rendering history will show the
  rewrite, not what the recruiter literally typed. If product ever needs the
  literal input shown to the user, this ADR must be reopened before building it.

## Alternatives considered

- **Persist the original and use the neutral rewrite only for the single
  `invoke` call** — the model would answer the neutral question once, but every
  later turn would pull the hostile original back into context, reintroducing
  exactly the framing the guardrail exists to strip. Rejected.
- **Store both versions in state** (original plus rewrite, e.g. a side channel
  keyed by message id) — preserves provenance, but adds state complexity that
  nobody consumes today: no endpoint, script, or prompt reads the original
  after the rewrite. Rejected as speculative; a future audit or telemetry need
  would reopen this ADR rather than be pre-accommodated here.
