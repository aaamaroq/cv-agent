# CV Agent — Interactive AI Portfolio

An AI-powered portfolio that lets recruiters explore Adrián Amaro’s experience
through a conversational CV assistant.

**Purpose:** make CV information easier to explore while demonstrating how to
build a grounded, guarded, streaming LLM application.

## In 30 seconds

- **For recruiters:** ask about Adrián’s skills, projects, experience, or fit for
  a role. Answers are grounded in reviewed source material.
- **For technical readers:** inspect a Python/FastAPI service, a LangGraph agent
  with input and output guardrails, and a React chat UI with server-sent events.
- **Conversation context:** the browser sends a bounded history with each
  request. The server is stateless; reloading the page starts a new chat.
- **Privacy:** `cv.md` contains personal information, is gitignored, and is not
  included in the repository.

## For recruiters

The assistant is designed to answer questions about Adrián’s documented
experience. Recruiter profiles can tailor the introduction, suggested questions,
and emphasis for a role; they do not add unsupported experience or claims.

Try the general chat at `/` or, after starting the app locally, open the sample
profiles at `/p/acme` and `/p/conversational-crm-agentic-runtime`.

## For technical readers

### Stack

- **Backend:** Python, FastAPI, LangChain, LangGraph
- **Frontend:** React, Vite, Tailwind CSS v4
- **Inference:** OpenRouter, with separately configurable answer and guardrail
  models
- **Streaming:** Server-Sent Events (SSE)
- **Observability:** optional OpenTelemetry and Langfuse integrations; traces
  include a profile ID in metadata and a `profile:<id>` tag

### Request flow

`React UI → FastAPI → input guardrail → answer model → output guardrail → SSE`

The graph can deflect hostile or manipulative input, retry an answer once when
the output review finds an issue, and use a fallback when the retry is rejected.
Draft chatbot tokens are held until the output review accepts them; canned
deflections and fallback responses are streamed directly.

### Engineering decisions

- **Grounded answers:** the CV and generated project notes are the sources of
  truth. Prior assistant messages are context, not evidence.
- **Stateless turns:** the browser keeps up to 11 completed turns in the current
  page and sends them with each question. No conversation state is stored by the
  backend.
- **Reviewed recruiter profiles:** role criteria and evidence maps stay
  server-side. Profile files are validated and loaded on demand.
- **Trace grouping:** each Langfuse trace includes `profile_id` metadata and a
  `profile:<id>` tag, and its session ID is prefixed with the profile ID.
- **Private content:** the CV is mounted at runtime and is not bundled into the
  backend image or committed to Git.

## Run locally

You need Python, Node.js, and an OpenRouter API key for live chat.

1. Create your private CV file from the template and add your own information:

   ```bash
   cp cv.md.sample cv.md
   ```

2. Start the API in one terminal:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   export OPENROUTER_API_KEY="your-openrouter-key"
   PYTHONPATH=src .venv/bin/uvicorn cv_chat.server:app --reload
   ```

3. Start the web app in another terminal:

   ```bash
   cd web
   npm install
   npm run dev
   ```

Open <http://localhost:5173>. The API runs at <http://localhost:8000>.

## Project documentation

- [Architecture decisions](ADR/)
- [Generated project brief](docs/PROJECT.md) — a factual summary derived from
  the codebase
- [Deployment guide](docs/deployment-continuation.md) — the documented target is
  a Vercel frontend and a Cloud Run API

<details>
<summary><strong>Build and evaluate</strong></summary>

Run the offline test suite:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

Run the guardrail evaluation ladder (requires a configured OpenRouter key):

```bash
PYTHONPATH=src .venv/bin/python scripts/guardrail_probe.py
```

Run the local development stack with automatic reloads:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

</details>

<details>
<summary><strong>Recruiter profiles</strong></summary>

Profiles live in `profiles/*.json`. A profile can customize the greeting,
questions, and answer emphasis while keeping its criteria and evidence map on the
server. Generate a profile from a local UTF-8 job-offer text file:

```bash
OPENROUTER_API_KEY="your-openrouter-key" PYTHONPATH=src \
  .venv/bin/python scripts/build_profile.py \
  --id acme-ai-engineer --company Acme --role "AI Engineer" \
  --offer /path/to/job-offer.txt
```

The generator sends the offer, CV, and project notes to the configured
OpenRouter model. It validates quoted criteria and evidence, but does not store
the raw offer. Review the generated profile before using it.

</details>

<details>
<summary><strong>Local Docker and observability</strong></summary>

The full local Compose stack runs the app and a self-hosted Langfuse instance.
Copy `.env.example` to `.env`, provide the OpenRouter key, and replace the local
service secrets before starting it:

```bash
docker compose up --build
```

The app is at <http://localhost:8000>; Langfuse is at <http://localhost:3000>.
Local traces include model inputs and outputs, guardrail calls, retries, and
rejected drafts. Use this stack only for your own local debugging. OpenRouter
also receives prompts used to generate responses.

Langfuse currently runs locally only. The production goal is to expose it as a
separately managed Google Cloud service with authenticated access. Store
Langfuse's generated application/database secrets and the app's Langfuse API
secret in Google Secret Manager; do not hardcode credentials in source or bake
them into container images. The Google Cloud Langfuse deployment is not yet
implemented.

</details>

<details>
<summary><strong>Configuration and code map</strong></summary>

| Variable | Default | Purpose |
|---|---|---|
| `CV_MODEL` | `openai/gpt-oss-20b` | Answer model on OpenRouter (low reasoning effort) |
| `CV_GUARDRAIL_MODEL` | `openai/gpt-oss-20b` | Input/output review model |
| `OPENROUTER_API_KEY` | *(empty)* | Required for live model calls |
| `CV_TEMPERATURE` | `0.3` | Answer model sampling temperature |
| `CV_HISTORY_WINDOW` | `24` | Maximum browser-supplied history messages |
| `CV_LLM_TIMEOUT_S` | `60` | Model-call timeout in seconds |
| `CV_PATH` | `cv.md` | CV source file path |
| `CV_PROFILES_DIR` | `profiles` | Recruiter profile directory |
| `CV_LANGFUSE_ENABLED` | `true` | Enable Langfuse tracing when configured |
| `LANGFUSE_PUBLIC_KEY` | *(empty)* | Langfuse project key |
| `LANGFUSE_SECRET_KEY` | *(empty)* | Langfuse project secret |
| `LANGFUSE_BASE_URL` | *(empty)* | Langfuse API base URL |

Key files:

- `src/cv_chat/graph.py` — LangGraph nodes and routing
- `src/cv_chat/guardrails.py` — input classification and output review
- `src/cv_chat/server.py` — HTTP API and SSE endpoint
- `src/cv_chat/streaming.py` — graph-to-SSE event adapter
- `web/src/` — React portfolio and chat interface
- `scripts/guardrail_probe.py` — guardrail evaluation cases
- `Dockerfile.backend` — backend-only image for the Cloud Run deployment target

`docs/PROJECT.md` is generated; update it with
`.venv/bin/python scripts/gen_project_brief.py` after architecture changes.

</details>
