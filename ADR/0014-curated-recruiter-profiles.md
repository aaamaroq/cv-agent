# ADR 0014: Curated recruiter profiles without conversation resumption

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Recruiters should be able to open a company-specific portfolio link with a
tailored greeting, suggested questions, and answer emphasis. The profile must not
create unsupported claims about Adrián or the target company. The product should
not resume a conversation when a recruiter returns, avoiding persistent chat
storage and its additional infrastructure and privacy costs.

## Decision

- Use one shared portfolio page with a path such as `/p/acme`; profile slugs are
  resolved against a server-side allowlist in `profiles.py`.
- Expose only presentation data through `GET /api/profiles/{profile_id}`. Keep
  model-facing profile instructions server-side and pass them to each graph turn
  after resolving the slug.
- Treat profile context as relevance guidance only. Claims about Adrián remain
  grounded in `cv.md` and `docs/PROJECT.md`; profile configuration is not evidence
  about the company or its hiring requirements.
- Scope each graph thread by profile ID. The browser creates a fresh random
  thread ID on each page load, so the chat is not resumed after reload or return.
- Start with a fictional Acme demo profile and no database or response cache.

## Consequences

- New company profiles are content/configuration changes rather than separate
  pages or application deployments.
- The public endpoint cannot expose server-only prompt instructions, and unknown
  profile slugs fail with 404.
- The existing in-memory checkpointer still supports turns while a page is open;
  it does not provide durable history or cross-visit resumption.
- The shared page needs an SPA fallback for `/p/{profile_id}` in the packaged
  FastAPI deployment.

## Alternatives considered

- **Duplicate the React page for each company:** rejected because copy and
  behavior would drift across nearly identical pages.
- **Accept free-form role instructions from the browser:** rejected because the
  client must not control model instructions or source-of-truth policy.
- **Persist recruiter conversations:** rejected for this feature because
  returning visitors do not need chat continuity and durable storage would add
  cost and data-retention obligations.
