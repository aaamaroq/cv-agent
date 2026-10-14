# ADR 0003: Positioning is measured, not gated; subgraph extraction deferred

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Adrián's target role is AI engineer, so the assistant should surface the
AI/ML relevance of a CV fact when there is one — but only where it genuinely
applies and only for technical questions (per the user's rule: *"solo cuando
hagan preguntas técnicas"*, never forced). The output critic (`check_output`)
can already reject hostile framings, leaks and — since ADR 0002 — overclaims,
and a rejected draft triggers one retry before a canned fallback.

The tempting move is to let the critic *enforce* positioning too: mark
`ok=false` on a correct-but-generic technical answer that never names the AI
link. That directly conflicts with the "never force it" rule and with the
fail-open / one-retry budget: a small classifier rejecting honest answers
would burn retries and risk dropping good content into the fallback.

Two further cleanups were on the list (`Paso 3`): move the guardrail nodes into
their own subgraph, and replace the hand-rolled `format="json"` + `extract_json`
with `with_structured_output`.

## Decision

1. **Positioning is enforced by the generator, measured by the probe — never
   gated by the critic.** The system prompt (ADR 0002) already asks the model
   to phrase the AI connection itself on technical questions. The probe adds a
   `positioned` case whose helper (`AI_RELEVANCE_RE`) reports PASS when the
   answer makes an AI/ML connection and **REVIEW — not FAIL — when it does
   not**, so we see regressions without punishing honest plain answers.
2. **Defer both `Paso 3` items until a live run can validate them.** Neither
   can be smoke-tested offline, and both touch load-bearing paths:
   - A subgraph around `output_guardrail` would nest its updates, breaking the
     SSE `restart` signal the server reads today (`server.py`, the
     `output_guardrail` key in `stream_mode="updates"`).
   - `with_structured_output` changes the exact JSON mechanism ADR 0001 had to
     hand-calibrate (the format-line verdict anchoring bug); swapping it blind
     risks re-introducing that failure class.

## Consequences

- Recruiter answers stay honest and neutral-first; AI framing emerges from the
  prompt nudge where it applies, with no forced bridges and no wasted retries.
- Positioning drift is visible in `scripts/guardrail_probe.py` output as REVIEW
  lines, a human-read signal rather than a silent regression.
- The retry loop and the JSON contract stay untouched and continue to be
  verified by the probe ladder on a real model.
- `Paso 3` becomes a follow-up gated on an authorized live probe run.

## Alternatives considered

- **Critic-gated positioning** — strongest enforcement, but violates "never
  force it," costs retries, and turns good answers into fallbacks. Rejected.
- **Do `Paso 3` blind** — faster, but ships an unverifiable change to the SSE
  streaming contract and the calibrated guardrail JSON. Rejected in favor of
  doing it alongside a real probe run.
