# ADR 0012: Update OpenRouter model defaults

- **Status:** Accepted
- **Date:** 2026-10-29
- **Supersedes:** ADR 0004's model defaults only; the OpenRouter provider decision
  and all other decisions in ADR 0004 remain in effect.

## Context

ADR 0004 selected free-tier OpenRouter models for the chat and guardrail calls.
Those models are no longer available on the free tier, so the recorded defaults
no longer provide a reliable out-of-the-box configuration. Model IDs remain
overridable through `CV_MODEL` and `CV_GUARDRAIL_MODEL`.

## Decision

- Set both defaults to `mistralai/mistral-nemo` until another available model is
  selected deliberately.
- Keep the answer and guardrail model settings independently configurable even
  though they currently share a default.
- Treat provider availability and pricing as operational facts that may change;
  verify current pricing in OpenRouter rather than assuming a free tier.

## Consequences

- A working OpenRouter account and API key are required for live requests, and
  calls may incur charges.
- Langfuse cost estimates are informational and depend on matching model pricing;
  compare them with provider billing.
- The prior model IDs and free-tier limits remain documented historically in
  ADR 0004.

## Alternatives considered

- **Keep the old `:free` IDs:** rejected because they are no longer available on
  the free tier.
- **Hard-code a paid model without environment overrides:** rejected because
  model availability and pricing can change.
