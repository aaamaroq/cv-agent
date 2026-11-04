# ADR 0013: Use Mistral Nemo for answers and Llama for guardrails

- **Status:** Accepted
- **Date:** 2026-11-04
- **Supersedes:** ADR 0012's answer and guardrail model defaults.

## Context

The original `mistralai/mistral-nemo` / Nemo configuration completed all 15
prepared cases but included unsupported personal stories and a language mismatch.
Staged experiments then tested Llama 3.1 8B as the answer model with Nemo as the
guardrail, and both models on Llama. The former failed the human-labelled
adoption threshold; the latter produced repeated generic fallbacks and missed
some unsupported claims. A direct guardrail-only comparison over saved Nemo
answers found that Llama blocked invented disagreement/stress stories and
accepted a grounded Spanish MCP answer, but did not catch a Kafka/pipeline
conflation. The LLM judge is not calibrated and is not used for this decision.

On 2026-11-04, a targeted end-to-end run of the hybrid configuration confirmed
the remaining gaps: Q04 was corrected after one retry, Q05 reached the generic
fallback after two retries, Q11 passed in Spanish, and Q15 invented Kafka use in
the Spark pipeline. The Q15 result motivated a deterministic claim check and a
more explicit prompt rule. A single rerun then produced a qualified Spanish
answer for Q15 without retries. Q05's fallback was made specific to the missing
stress/deadline evidence and is covered offline; it was not re-run live to avoid
another paid call.

## Decision

- Set `CV_MODEL` to `mistralai/mistral-nemo` for answers.
- Set `CV_GUARDRAIL_MODEL` to `meta-llama/llama-3.1-8b-instruct` for input and
  output guardrails. Keep both settings independently overridable.
- Enforce response-language matching deterministically before the output
  classifier. For the documented Kafka/Spark case, reject claims linking Kafka
  to the order-processing pipeline unless they state the evidence boundary.
- Use question-specific safe fallbacks for the prepared deadline/stress and
  Kafka/pipeline gaps.
- Keep human labels and the prepared acceptance criteria authoritative. Do not
  use the uncalibrated LLM judge or the targeted results as a full-dataset score.

## Consequences

- The runtime defaults and local `.env` use the hybrid configuration; README,
  `.env.example`, config tests and generated project notes must agree.
- Targeted evidence now covers Q04, Q05, Q11 and Q15. Q05's final fallback has
  offline coverage only. A full hybrid run remains a separate, cost-bearing
  regression check and is not implied by this decision.
- The deterministic Kafka check is intentionally narrow and grounded in the CV:
  Kafka is listed as a skill, while the order-processing pipeline is documented
  as using Spark. Revisit it if the source CV changes.
- OpenRouter availability, latency and pricing remain operational facts to
  verify; run targeted cases before spending on a broader evaluation.

## Alternatives considered

- **Use Nemo for both models:** rejected because Nemo passed invented personal
  stories and the Kafka/pipeline claim.
- **Use Llama for both models:** rejected because of false rejections, generic
  fallbacks and poor completion in the prepared evaluation.
- **Use Llama for answers and Nemo for guardrails:** rejected because the
  human-labelled answer-model comparison did not meet the adoption threshold.
