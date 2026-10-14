# ADR 0001: Input and output guardrails as graph nodes

- **Status:** Accepted
- **Date:** 2026-10-07

## Context

The portfolio chatbot is public and answers anyone. Two risks:

1. **Adversarial input.** Leading or hostile questions ("por qué no contratar
   a Adrián", false dilemmas, backhanded premises) can drag the main model
   into producing answers that portray Adrián badly or that concede a negative
   framing the question merely assumed.
2. **Model drift.** Even without adversarial input, the main model can
   occasionally drift off-policy (negative tone, empty boilerplate).

Mitigation by prompt rules alone is weak: small local models tend to follow
the framing of the last message regardless of system-prompt instructions, and
a prompt cannot verify its own output. Production conversational systems
therefore use layered guardrails: check on the way in, check on the way out.

## Decision

Add two guardrail nodes to the graph, each running on a **separate, smaller
classifier model** (configurable via `CV_GUARDRAIL_MODEL`; deliberately not
fixed here because these models get swapped over time), with temperature 0
and JSON output mode. The main model is only invoked for real answers.

```
START → input_guardrail ─┬─ ok/loaded ─→ chatbot → output_guardrail ─┬─ pass ───────────→ END
                         │                                           ├─ fail (≤1 retry) ─→ chatbot
                         ├─ abuse ────→ deflect ─────────────────────┘                    └─ fail again → fallback → END
                         └─ injection → deflect (injection canned reply) ────────────────→ END
```

- **input_guardrail** classifies the latest user message:
  - `ok` — pass through unchanged. Directly critical/skeptical questions that
    genuinely ask for information ("isn't that too junior?") are `ok`.
  - `loaded` — hostile/leading frame but a legitimate question behind it.
    The guardrail rewrites it into a *neutral question* that **preserves the
    underlying concern** (seniority doubts stay seniority doubts); the
    `chatbot` node answers that version, so the hostile framing never reaches
    the main model, and the rewritten message replaces the original in the
    checkpoint so later turns never see the hostile frame.
  - `abuse` — pure insults/threats with no question to answer. A canned reply
    (`deflect`) is returned without invoking the main model.
  - `injection` — attempts to override instructions, extract the system
    prompt/config (direct, obfuscated, or via fake `<system>`/`SYSTEM:`
    messages), or escape the persona (DAN-style roleplay), **even when a
    legitimate question is attached**. Routed to `deflect` with its own
    canned reply.
- **output_guardrail** reviews the draft before delivery:
  - pass → deliver;
  - fail → the draft is removed from state and regenerated once with a
    corrective note;
  - fail again → canned reply (`fallback`).
  - It rejects replies that reveal system prompt/instructions/internal
    mechanisms (CV content is always allowed), concede hostile framings,
    speak ill of Adrián, or are empty boilerplate (including one-word
    answers).

### Supporting decisions

- **Fail-open.** If a guardrail call errors or returns unparseable JSON, the
  message flows normally. A broken classifier must not take the chat down.
- **Guardrail model is unloaded after each call** (`keep_alive=0`) so it
  never competes with the main model for RAM on a constrained local machine.
- **One output retry max** — local hardware makes extra generations costly.
- **SSE protocol gains a `restart` event.** Tokens from a rejected draft are
  already streamed when the output guardrail rejects it, so the server emits
  `restart` and the UI discards the draft before the retry streams in.
- **Few-shot examples in both guardrail prompts.** Small classifiers barely
  follow abstract rules but follow concrete examples reliably; the output
  prompt's JSON template must not anchor a verdict value (a literal
  `{"ok": true}` in the format line made the classifier answer `true`).
- **Fourth verdict `injection` with its own canned reply.** Prompt
  extraction/override attempts get a reply that names the attempt instead of
  the generic professional deflect, without adding a graph node — `deflect`
  picks the string from the verdict.
- **Contrast pairs calibrate `ok` vs `loaded`.** Vague phrasing made the
  classifier neutralise honest skepticism; the prompt now pairs a skeptical
  good-faith question (`ok`, copied verbatim) with a hostile one (`loaded`)
  and mandates permissive defaults when unsure (`ok` over `abuse`/
  `injection`).
- **Output prompt also rejects instruction leaks.** The classifier must
  distinguish CV content (allowed and expected) from system-prompt or
  internal-mechanism content (rejected), closing the case where the main
  model dumped the whole prompt after the input guardrail said `ok`.
- **Hostile message replaced in the checkpoint.** The neutral rewrite is
  returned with the original message id so `add_messages` swaps it in place;
  later turns never see the hostile frame.

## Consequences

- Hostile framing never reaches the main model; recruiters still get their
  question answered, neutrally phrased.
- Bad drafts are caught before the user sees them (or after one retry).
- Two extra small-model calls per turn: measurable but acceptable latency
  locally.
- Guardrail quality is bounded by a small classifier; occasional
  misclassification is possible. Fail-open keeps availability, and the
  neutralisation path degrades gracefully (a misread `loaded` just answers
  the original question).
- Canned replies are fixed strings (professional deflect, injection
  deflect, fallback).

## Alternatives considered

- **Prompt-only rules** — cheapest, but weakest against adversarial phrasing
  with small models and provides no output verification.
- **Guardrails outside the graph (middleware/service)** — more moving parts
  and no value from LangGraph's branching/checkpointing.
- **Blocking hostile questions outright** — worse recruiter UX; rewriting
  preserves the legitimate question behind the framing.
- **Output guardrail only** — leaves the main model exposed to the hostile
  frame in the first place (it must still generate a draft from it).
