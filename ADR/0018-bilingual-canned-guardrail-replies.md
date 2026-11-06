# ADR 0018: Answer blocked turns in the recruiter's language

- **Status:** Accepted
- **Date:** 2026-11-06
- **Refines:** ADR 0001's consequence that canned replies are fixed strings.

## Context

A Spanish-speaking visitor received an English reply: "Let's keep this
professional — I'm here to answer questions about Adrián's experience...".
That text is `DEFLECT_MESSAGE`, emitted only when the input guardrail returns
`abuse` (or `injection`, which has its own canned text).

The `deflect` node ends the turn before the chat and output models run, so the
usual language guarantees never apply to it:

- the answer prompt's "answer in the user's language" rule is never read;
- `language_mismatch()` only inspects model drafts, not canned text;
- the canned strings themselves were English-only, while `fallback_message()`
  was already bilingual.

Two independent problems produced the English reply: the small input classifier
can read a Spanish meta-request ("háblame en español", "why do you answer in
English?") as an attempt to manipulate the bot, and the canned reply had no
Spanish variant to fall back to.

## Decision

- Keep the canned replies, but make them bilingual: `DEFLECT_MESSAGE_ES` and
  `INJECTION_MESSAGE_ES` mirror their English counterparts.
- Choose the language at emission time with `guardrails.deflect_message(
  question, verdict)`, using the existing `is_spanish_text()` heuristic. The
  decision belongs to `deflect` because it is the only place that still sees the
  recruiter's message.
- State in the input rubric that questions about the conversation itself
  (asking for Spanish/English, noting the reply language, asking to repeat or
  clarify) are legitimate `ok`/`loaded` messages, never `abuse` or `injection`,
  and add Spanish few-shot examples.
- Extend `is_spanish_text()` with unambiguous Spanish function words so short,
  unpunctuated messages ("hola", "gracias", "puedes", "quiero", "dime") are
  detected without relying on `¿`/`¡`.
- Teach `scripts/guardrail_probe.py` to recognize both language variants when
  it labels a reply as a deflection or fallback, and add a probe case for a
  language request and a language complaint.

## Consequences

- Spanish visitors get the block message in Spanish without an extra model
  call, latency, or token cost.
- The language check for blocked turns is still heuristic: a very short message
  with none of the recognized markers can still receive the English variant.
  It never affects the answer language itself, only the canned block/fallback.
- `is_spanish_text()` now also feeds `language_mismatch()` and
  `fallback_message()`, so any new marker must be unambiguous Spanish to avoid
  treating an English draft as Spanish.
- The output guardrail still cannot review canned text; the bilingual strings
  are trusted constants, and `scripts/eval_judge.py` keeps its "English canned
  deflection for a Spanish question" penalty as a regression signal.

## Alternatives considered

- **Translate the canned text in the UI from the interface locale:** rejected
  because the recruiter's language and the UI language are independent (a
  Spanish recruiter can use the English UI and vice versa).
- **Ask the main model to write the block message:** rejected because it
  reopens the attack surface the guardrail exists to close and adds latency and
  cost to a turn that should be instant.
- **Use a dedicated language-detection dependency:** rejected for now; the
  heuristic covers the supported Spanish/English pair, and a new dependency is
  not justified before real traffic shows it is needed.
- **Drop the block messages and answer everything:** rejected because pure
  abuse and prompt injection still need a terminal, non-model response.
