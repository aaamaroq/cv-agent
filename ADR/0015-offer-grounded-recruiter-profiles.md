# ADR 0015: Offer-grounded recruiter profiles with an unchanged general portfolio

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Recruiters need to evaluate how Adrián's experience relates to a particular job,
while the root portfolio must remain useful for visitors who arrive without a
specific offer. A list of overlapping keywords is not enough to support a fit
answer: professional experience, personal projects, listed skills, and training
have different evidential weight. The assistant must not promote transferable or
unverified experience to a demonstrated job skill.

The original job offer may contain company or customer details that should not be
copied into the public profile artifact. Raw offer text and exact offer quotes
must not be available to the runtime.

## Decision

- Keep the `general` profile empty of offer criteria. The root route retains its
  existing AI Engineering portfolio title, greeting, questions, and general
  evidence context; it must not inherit criteria from personalized routes.
- Store custom profiles as JSON under `profiles/`. A customized profile may
  contain a sanitized role rubric, a factual positioning summary, positive
  recruiter-oriented question starters, and an evidence map.
- Generate custom profiles locally with `scripts/build_profile.py`. It sends
  the offer, CV, and generated project notes to the configured OpenRouter model
  for one-time structured extraction. Exact offer quotes are validated but not
  stored. Exact CV/project evidence quotes are stored in the server-side profile
  map with an evidence type and a direct/related/listed/training relation.
- Treat offer criteria as facts about the role, never as candidate evidence.
  At runtime, verify mapped candidate claims against `cv.md` and
  `docs/PROJECT.md`. Keep professional experience, personal projects, skills,
  and training distinct. A related match is transferable evidence, not proof of
  the exact requirement.
- Permit a measured comparison only when a recruiter asks about fit and a
  customized profile supplies role criteria. The answer should lead with the
  strongest relevant professional evidence, use personal projects as clearly
  labeled complementary evidence, and qualify a materially unverified required
  criterion when needed. Do not make a hiring decision or volunteer a list of
  weaknesses. With the general profile, answer about documented strengths but
  do not claim fit to an unspecified role.
- Keep the portfolio title constant across routes. Personalized pages change
  their positioning, friendly greeting, and suggested questions, not the title.
- Expose presentation fields only through `GET /api/profiles/{profile_id}`.
  Keep criteria and the evidence map server-side. Do not persist raw offers or
  offer quotes in profile JSON.
- Do not automate profile freshness checks; regenerate and review a profile
  manually when its offer or evidence changes.

This decision supersedes ADR 0014's rule that recruiter profiles may only
prioritize general evidence and must not contain job requirements. Its choices
about profile routing, public payloads, thread scoping, and non-persistent chat
remain in force.

## Consequences

- The default portfolio stays role-agnostic; fit answers on a personalized link
  can compare evidence with the selected role criteria.
- Profile generation is still a one-time model call and requires human review,
  especially for relevance labels, positioning, and any claimed fit.
- The exact CV/project evidence map is available to server prompts but not
  returned by the public profile endpoint. The public profile still contains
  sanitized requirements and display copy only.
- Exact quote validation confirms that candidate excerpts exist in the selected
  source; it does not prove that the model's relevance classification is
  correct. Human review remains required.
- A role criterion without mapped evidence remains a criterion, not a candidate
  claim. If directly asked, the assistant can state that the available sources
  do not document the specific experience without claiming it does not exist.

## Alternatives considered

- **Keep only keyword themes:** rejected because they cannot support a grounded
  comparison between role criteria and evidence.
- **Use one offer-specific profile as the root experience:** rejected because
  visitors without that offer need a general portfolio and must not inherit its
  requirements.
- **Show public question starters about missing skills:** rejected because
  starters should surface the recruiter’s positive, decision-oriented questions;
  evidence limits are handled honestly when they materially affect an answer.
- **Store the full offer or its exact quotes:** rejected to avoid publishing
  identifying offer details and adding unnecessary runtime context.
- **Generate a binary fit score or hiring verdict:** rejected because direct,
  related, and unverified evidence cannot be reduced responsibly to a single
  model-generated score or final decision.
