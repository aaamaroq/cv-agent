# ADR 0016: Stateless chat turns and Cloud Storage content

- **Status:** Accepted
- **Date:** 2026-11-05

This decision supersedes the conversation-memory and per-thread lifecycle choices
in ADRs 0007, 0008, and 0014. Those records remain unchanged as design history.

## Context

The portfolio is deployed as a static Vite app on Vercel and a FastAPI service
on Cloud Run with minimum instances set to zero. In-process LangGraph memory
cannot reliably preserve a conversation when Cloud Run scales down or replaces
an instance. Recruiter chats are short and should not require a database or a
warm backend. The CV and curated recruiter profiles must also be deployable and
updatable independently of the backend image.

## Decision

- Keep completed conversation turns in the browser for the lifetime of the
  current page, send a bounded transcript with each chat request, and compile the
  LangGraph without a checkpointer. The transcript is context only; the system
  prompt and output guardrail continue to treat the CV and project notes as the
  only sources of truth. A page reload starts a new conversation.
- Keep the random `thread_id` as a trace/session label only; it does not identify
  backend-persisted state.
- Run Cloud Run with minimum instances zero and an initial maximum of one. A
  generic `GET /api/warmup` request wakes the service without blocking the
  portfolio render or exposing configuration details.
- Mount a private Cloud Storage bucket read-only at `/mnt/cv-content`. Store
  `cv.md` at the mount root and curated profile JSON files under `profiles/`.
  Configure `CV_PATH` and `CV_PROFILES_DIR` to those mounted paths. Load profile
  files on demand, with ID/filename and evidence-reference validation, so newly
  uploaded reviewed profiles are visible without rebuilding or redeploying the
  image.
- Deploy a backend-only image to Cloud Run. Let Vercel host the static frontend,
  proxy `/api/*` to the Cloud Run URL, and route direct `/p/{profile_id}` visits
  to the SPA entry point.
- Give the Cloud Run service identity read-only bucket access. Keep
  `OPENROUTER_API_KEY` in Secret Manager and configure model IDs as Cloud Run
  environment variables.

## Consequences

- The app remains usable while Cloud Run is cold; the first API interaction may
  still incur a cold start.
- Browser-held history survives backend restarts while the page remains open,
  but is lost on reload. No conversation data is persisted server-side.
- Requests are independently processable, avoiding session affinity and
  single-instance memory requirements. The transcript is size-limited and
  validated as complete user/assistant turns.
- Cloud Storage FUSE makes the CV and profile objects available through normal
  file reads. New objects may be delayed by mount metadata caching unless that
  cache is configured for the desired freshness.
- The public health response is intentionally generic; the frontend uses the
  dedicated no-detail warm-up endpoint instead.

## Alternatives considered

- **Keep `MemorySaver` and pin one warm Cloud Run instance:** rejected because
  minimum instances cost continuously and can still restart; minimum zero can
  lose state between messages.
- **Use a shared database checkpointer:** rejected for the initial low-volume,
  short-lived recruiter chat because browser-held context avoids a database and
  retention policy.
- **Bundle the CV and profiles into the image:** rejected because the CV is
  gitignored and new profiles should not require an image rebuild.
- **Expose a profile upload API:** rejected; uploads remain an owner/operator
  action, with only reviewed JSON objects placed in the private bucket.
