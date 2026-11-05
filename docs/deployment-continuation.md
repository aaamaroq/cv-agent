# Deployment architecture — continuation notes

Updated: 2026-11-05

## Goal

Publish the portfolio on Vercel and the FastAPI chatbot on Google Cloud Run. Keep
the frontend responsive on first visit without paying to keep the backend warm,
and allow new recruiter profiles to be added without rebuilding the app image.

## Direction agreed

- **Frontend:** deploy `web/` to Vercel as a static Vite app.
- **Backend:** deploy `Dockerfile.backend` to Cloud Run with minimum instances
  zero and maximum instances one. Cold starts are acceptable; the frontend does
  not wait for the backend before rendering.
- **Warm-up:** on initial page load, fire an asynchronous, non-blocking request to
  `GET /api/warmup`. It returns no operational details and does not call an LLM.
  It may wake the service for visitors who leave and does not guarantee the
  service is warm if a message is sent immediately.
- **Recruiter profile links:** `/p/{profile_id}` continue to be frontend routes.
  Today, personalized routes already call `/api/profiles/{profile_id}` on page
  load, which will also wake the backend. The general portfolio route currently
  makes no API call on load, so it needs the warm-up request.
- **Chat history:** the browser sends a bounded history of completed turns with
  each request. The graph is stateless; a Cloud Run restart cannot erase context
  while the page remains open. Reloading starts a new chat.
- **Configuration:** set `CV_MODEL`, `CV_GUARDRAIL_MODEL`, `CV_PATH`, and
  `CV_PROFILES_DIR` in Cloud Run; provide `OPENROUTER_API_KEY` from Secret
  Manager. Updating settings creates a new Cloud Run revision but does not
  require rebuilding the image.

## Dynamic profiles without image rebuilds

`src/cv_chat/profiles.py` loads the requested JSON file on demand from the
configured profile directory. Mount one private Cloud Storage bucket read-only
at `/mnt/cv-content`; set `CV_PATH=/mnt/cv-content/cv.md` and
`CV_PROFILES_DIR=/mnt/cv-content/profiles`. The backend image does not bundle
the CV or recruiter profiles.

1. Give the Cloud Run service account `roles/storage.objectViewer` on the bucket.
   Keep write access restricted to the owner/operator; there is no public upload
   endpoint.
2. Upload the CV and reviewed profile JSON objects, e.g. `gcloud storage cp
   cv.md gs://BUCKET/cv.md` and `gcloud storage cp profiles/example.json
   gs://BUCKET/profiles/example.json`.
3. Use the Cloud Storage volume mount options `implicit-dirs` and
   `metadata-cache-ttl-secs=0` so newly uploaded objects are read from the
   current bucket contents. Profiles are read and validated on demand; ID must
   match the filename and evidence must reference an existing requirement.

After the initial Cloud Run configuration, uploading a new reviewed profile
object should make it available without a Docker build or Cloud Run revision.
Do not upload the raw job offer.

## Repository implementation status

- **API routing and SPA fallback:** implemented in `web/vercel.json`. Set
  `CV_API_URL` in Vercel Production and Preview environments to the Cloud Run
  service URL without a trailing slash. `/api/*` is proxied on the same origin;
  `/p/{id}` falls back to the React app, so browser CORS is not needed.
- **Warm-up and health:** `/api/warmup` returns 204 with no body. `/api/health`
  now returns only `{"status":"ok"}`; it does not expose model names or
  configuration-presence flags.
- **Image layout:** `Dockerfile.backend` builds FastAPI only. The existing
  `Dockerfile` remains for the local combined Compose setup.
- **Observability:** the Langfuse Compose stack remains local debugging only.
  Decide later whether to disable tracing in production or use hosted Langfuse.

## Remaining deployment steps

1. Create a private Cloud Storage bucket and upload `cv.md` and reviewed
   `profiles/*.json` objects.
2. Grant the Cloud Run service account `roles/storage.objectViewer` on that
   bucket.
3. Build and push the API image with `Dockerfile.backend`, then deploy Cloud Run
   with minimum instances `0`, maximum instances `1`, the read-only bucket mount,
   `CV_PATH`, `CV_PROFILES_DIR`, model variables, and the Secret Manager mapping
   for `OPENROUTER_API_KEY`.
4. Set `CV_API_URL` in Vercel Production and Preview and deploy the `web/`
   directory as the Vite app.
5. Verify `/`, a direct `/p/{id}` visit, a profile upload appearing without a
   redeploy, warm-up, SSE chat, and a multi-turn conversation when Cloud Run has
   scaled to zero between requests.

Example Cloud Run deployment command (replace the uppercase placeholders):

```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/REPOSITORY/cv-chat:latest \
  --file Dockerfile.backend

gcloud run deploy cv-chat-api \
  --image REGION-docker.pkg.dev/PROJECT/REPOSITORY/cv-chat:latest \
  --region REGION \
  --service-account cv-chat-runtime@PROJECT.iam.gserviceaccount.com \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --min 0 --max 1 \
  --memory 1Gi --cpu 1 \
  --set-env-vars "CV_MODEL=mistralai/mistral-nemo,CV_GUARDRAIL_MODEL=meta-llama/llama-3.1-8b-instruct,CV_PATH=/mnt/cv-content/cv.md,CV_PROFILES_DIR=/mnt/cv-content/profiles,CV_LANGFUSE_ENABLED=false" \
  --set-secrets "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest" \
  --add-volume "mount-path=/mnt/cv-content,type=cloud-storage,bucket=BUCKET,readonly=true,mount-options=implicit-dirs;metadata-cache-ttl-secs=0"
```

Before deploying, grant `roles/storage.objectViewer` on `gs://BUCKET` to the
runtime service account and grant that account access to the `OPENROUTER_API_KEY`
secret. In Vercel, set `CV_API_URL` to the resulting Cloud Run service URL in
both Production and Preview, then redeploy the `web/` project.

The Cloud Run volume-mount documentation is at
<https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts>.
Vercel's route environment-variable syntax is documented at
<https://vercel.com/docs/project-configuration/vercel-json>.

When implementation adds a config environment variable, dependency, endpoint, or
other architecture item covered by `AGENTS.md`, regenerate `docs/PROJECT.md`.
