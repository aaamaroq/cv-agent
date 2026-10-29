# ADR 0010: Hot reload for local Docker development

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The packaged Compose app builds the React assets into the API image and does
not mount application source. Code edits therefore require rebuilding the
image before they can be tested.

## Decision

- Keep the existing Compose stack as the packaged, production-like local run.
- Add a Compose development overlay with a reload-enabled FastAPI container,
  bind-mounted Python/project sources, and a Vite dev server container.
- Proxy Vite API requests to the API service over the Compose network.
- Build separate development images so the production app image and runtime
  remain unchanged.

## Consequences

- UI edits under `web/src` appear through Vite without rebuilding.
- Python edits under `src` and project-note edits under `docs` restart FastAPI.
- Dependency changes still need image rebuilds; Langfuse and its backing
  services continue to run in the same Compose stack.

## Alternatives considered

- Rebuild the packaged app image after every edit: rejected because it slows
  the edit/test loop.
- Run API and UI directly on the host: rejected because the requested workflow
  is to run the whole stack in Docker.
