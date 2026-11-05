# ADR 0017: Use gpt-oss-20b for answers and guardrail checks

- **Status:** Accepted
- **Date:** 2026-11-05
- **Supersedes:** ADR 0013's answer-model choice; ADR 0017's prior text is
  expanded to include the guardrail decision after the Jev comparison.

## Context

The portfolio's Mistral Nemo answer model is too slow for the desired chat
experience, and the output guardrail adds another latency and rejection loop.
`CV_MODEL` is independently configurable through OpenRouter, and
`ChatOpenRouter` supports a configurable reasoning effort for gpt-oss models.

We also tested `typesafe/jev-1.14` as a stricter alternative guardrail on the
same 15-case evaluation set used for the real graph. The goal was to determine
whether Jev materially outperformed a self-guardrail approach using the same
`openai/gpt-oss-20b` model.

## Decision

- Use `openai/gpt-oss-20b` as the default answer model.
- Set its reasoning effort to `low` to prioritize response latency for grounded
  CV questions. Apply this setting only when the selected model is gpt-oss-20b.
- Use `openai/gpt-oss-20b` as the default input and output guardrail model as
  well. The guardrail remains the same model as the answer model unless a
  dedicated override is configured explicitly.
- Keep `CV_MODEL` and `CV_GUARDRAIL_MODEL` independently overridable.
- Treat `typesafe/jev-1.14` as an experimental stricter guardrail, not the
  default production choice. It was evaluated against the same dataset but was
  found to be more conservative and to trigger more fallbacks and deflections
  without a clear quality advantage over the gpt-oss-20b self-guardrail.

## Evidence from the comparison

The real graph was executed against the same 15-case evaluation set with two
configurations:

- gpt-oss-20b answer model + gpt-oss-20b guardrail
- gpt-oss-20b answer model + Jev 1.14 guardrail

The observed results were:

- gpt-oss-20b self-guardrail: 15/15 OK, 14 output-accepted, 5 retries, 1
  fallback, 0 deflections, 195,668 total tokens, 113.3s total latency.
- gpt-oss-20b + Jev: 15/15 OK, 7 output-accepted, 14 retries, 7 fallbacks,
  1 deflection, 85,021 total tokens, 68.8s total latency.

The Jev run was more defensive and less helpful in practice. It rejected or
redirected more cases than the gpt-oss-20b self-guardrail while delivering no
clear evidence of better groundedness on this dataset. The self-guardrail also
performed better in multiple cases that required grounded, source-based answers
without excessive fallback.

## Consequences

- The default, `.env.example`, local `.env`, deployment instructions, README,
  config tests, and generated project notes must agree on gpt-oss-20b as the
  default answer and guardrail model.
- Low reasoning effort is a speed/quality tradeoff and may need adjustment if
  prepared CV-answer cases expose a reasoning gap.
- Output text remains buffered until the guardrail approves it; changing models
  alone does not enable visible token-by-token streaming.
- OpenRouter routing, latency, and price must continue to be observed from real
  traffic, especially if the provider or model route changes.
- Jev remains available for controlled security-minded experiments, but it is
  not the chosen production default.

## Alternatives considered

- **Keep Nemo and route with `:nitro`:** rejected as the first choice because it
  retains the slow model and may select a higher-priced priority endpoint.
- **Keep Llama as the guardrail:** rejected after the comparison with the
  gpt-oss-20b self-guardrail and the Jev benchmark; it is less competitive in
  the real decision loop than the current default.
- **Use Jev as the default guardrail:** rejected because it is more
  conservative, triggers more fallback and deflection, and does not show a
  consistent quality advantage over the gpt-oss-20b guardrail on the prepared
  evaluation set.
- **Stream unreviewed tokens immediately:** rejected here because it would show
  text before the output guardrail has accepted it.
