# Deploying BankSense: Vercel + Fly.io + Supabase

This is the production deployment path:

- **Vercel** hosts the static React/Vite frontend.
- **Fly.io** runs the Docker image from `backend/Dockerfile`: FastAPI, CPU
  PyTorch, Sentence Transformers, and both trained classifiers.
- **Supabase** provides PostgreSQL, Google authentication, and row-level
  security (RLS).

The frontend and backend are separate origins. The browser calls the Fly.io
HTTPS URL directly, and the backend allows exactly the Vercel origin through
CORS. Supabase auth/RLS is unchanged: the browser sends the user's JWT and the
backend forwards it to Supabase PostgREST. No service-role key is used for
normal traffic.

```text
Browser
  -> Vercel static site (React/Vite)
  -> Supabase Auth (Google OAuth)
  -> https://<fly-app>.fly.dev/api/* (Bearer access token)
       -> FastAPI + both NLP classifiers
       -> Supabase Data API with the user's JWT (RLS)
```

## Local vs production at a glance

| Step | Where | Production? |
|---|---|---|
| Put the five model files in `backend/models/` | Local machine | Preparation |
| Create `.env` from `.env.example` | Local machine | Local only |
| Build/run the Docker image | Local machine | Optional preflight |
| Create and deploy the Fly.io app | Fly.io | Production |
| Deploy the frontend | Vercel | Production |
| Set CORS and Supabase redirect URLs | Fly.io / Supabase | Production |
| Run the acceptance checks | Browser / terminal | Production |

Never commit `.env`, `model.zip`, or the extracted model artifacts.

## Why the backend runs on Fly.io

The backend installs roughly **1.0 GB** of Python packages. CPU PyTorch alone is
about **718 MB** installed. A standard Vercel Python function has a **500 MB**
uncompressed bundle limit, so it cannot hold this app. Fly.io runs the existing
container image with a persistent 2 GB machine, which fits CPU torch, the SBERT
encoder, and both classifiers with headroom.

Measured footprint: about **556 MB RSS** with the SBERT encoder loaded. The
optional summariser is disabled in production because its weights are about
1.2 GB.

## Region and cost (checked November 2026)

Fly.io does **not** have a Mumbai (`bom`) region. The closest listed region to
India is **Singapore (`sin`)**. Tokyo (`nrt`) and Sydney (`syd`) are farther and
more expensive.

| Item | Monthly cost |
|---|---:|
| `shared-cpu-2x`, 2 GB RAM, always-on, `sin` | **$17.00** (30 days) |
| Same machine in a 31-day month | ~$17.57 |
| Volume (optional) | $0.15/GB/month |
| Outbound data, Asia Pacific | $0.04/GB; inbound free |
| Shared IPv4 + `.fly.dev` TLS | $0.00 |
| Dedicated IPv4 (not needed) | $2.00 |
| Fly image registry and builders | $0.00 currently |
| Supabase | $0 on the free tier |
| Vercel Hobby | $0 for personal, non-commercial use; Pro is $20/user/month |
| **Baseline total** | **about $17/month + egress** |

Notes:

- The 2 GB `shared-cpu-2x` price in `sin` is derived from Fly.io's published
  region markup (`sin` = 1.269230769 × the `iad` price of $13.39).
- **No volume is required.** The five model artifacts and the SBERT encoder are
  baked into the image. If you add a volume later, add $0.15/GB/month.
- New Fly.io organizations have no free tier. Bills under $5 are waived, but
  this deployment is above that threshold.
- The machine is kept warm (`auto_stop_machines = "off"`). Auto-stop would save
  money but add roughly 30 seconds to the first request after idle.

## Files added or changed

| File | Purpose |
|---|---|
| `vercel.json` | Frontend-only Vercel build (`frontend/dist`) |
| `.vercelignore` | Keeps `backend/`, model archives/binaries, data, and secrets out of the Vercel upload |
| `.gitignore` | Keeps `model.zip`, `*.joblib`, `*.npy`, and other model binaries out of Git |
| `backend/fly.toml` | `sin` region, 2 GB machine, always-on, auto-start, port 8080, `/` health check |
| `backend/Dockerfile` | CPU torch, artifact-derived SBERT encoder, non-root runtime, uvicorn on port 8080 |
| `backend/.dockerignore` | Keeps local Docker builds small |
| `backend/nlp/config.py` | Summary flag and artifact-authoritative SBERT encoder name |
| `backend/nlp/prefetch.py` | Validates `sbert_model_name.txt` and pre-fetches that exact encoder |
| `backend/nlp/summarizer.py` | Honors the flag and fails gracefully |
| `frontend/vite.config.js` | Strict production API-origin validation and local dev proxy |
| `.env.example` | Documents production backend/frontend values |

## Prerequisites

- A Fly.io account and the `flyctl` CLI.
- A Vercel account and Node.js/npm for the Vercel CLI.
- Docker Desktop, only for the optional local container test.
- The five genuine model files from `model.zip`:
  - `backend/models/tfidf_logreg.joblib`
  - `backend/models/sbert_logreg.joblib`
  - `backend/models/label_classes.json`
  - `backend/models/sbert_model_name.txt`
  - `backend/models/training_metadata.json`
- The Supabase project URL and publishable key. Do **not** paste secrets into
  chat, commit them, or put them in `fly.toml`. Use `fly secrets set` and the
  Vercel dashboard.
- The actual Vercel production domain (for example
  `https://<project>.vercel.app`). CORS and Supabase redirect URLs cannot be
  finalized until it is known.
- A local `.env` created from `.env.example` before running the optional Docker
  command with `--env-file .env`. `.env` is gitignored.

> **Repository ownership:** the GitHub repo is owned by Armaan. These steps use
> the Fly.io and Vercel CLIs, so you do not need to change repository ownership.
> Nothing is pushed to GitHub by this guide.

---

## Step 1 — Put the model files in place (local preparation)

From the repository root:

```powershell
Expand-Archive -Path model.zip -DestinationPath .
Get-ChildItem backend\models
```

You should see the five files listed above. `backend/models/` is gitignored.
`model.zip` and the extracted artifacts are also excluded from the Vercel
upload by `.vercelignore`.

Do **not** `git add` the model files. `fly deploy` uploads the local build
context, including gitignored files, and bakes them into the private image. They
are never served as public static files.

> A Git-based Fly.io deploy (for example, GitHub Actions) will **not** include
> `backend/models/` because it is gitignored. Deploy from a machine that has the
> files, or add a private build-time download step for the model archive.

## Step 2 — Test the container locally (local only, optional)

This step runs on your machine and does not deploy anything.

1. Create the local environment file from the template. The `docker run`
   command below uses `--env-file .env`, so this must exist first:

   ```powershell
   Copy-Item .env.example .env
   ```

   Fill in the local values you need. `.env` is gitignored and is never
   committed or uploaded to Vercel.

2. Start Docker Desktop, then from the repository root:

   ```powershell
   docker build -f backend/Dockerfile -t banksense-backend backend
   docker run --rm -p 8080:8080 --env-file .env -e BANKSENSE_ENABLE_SUMMARY=0 banksense-backend
   ```

3. In another terminal:

   ```powershell
   Invoke-RestMethod http://localhost:8080/
   Invoke-RestMethod http://localhost:8080/api/health
   ```

Expected with Supabase configured: `status=ok`, `database=ok`,
`auth=required`, both model flags `true`, and `summary=unavailable`.

If the build fails at the `test -s` step, one or more of the five model files
are missing, empty, or misnamed. The Docker build intentionally fails rather
than shipping an image without the real artifacts. Do not bypass those checks.

The build also runs `backend.nlp.prefetch`, which reads
`backend/models/sbert_model_name.txt`, verifies it against the SBERT artifact,
and pre-fetches exactly that encoder. If those checks fail, fix the artifacts
rather than editing the file to hide a mismatch.

## Step 3 — Create and deploy the Fly.io backend (production)

Install the CLI if needed (then reopen the terminal):

```powershell
iwr https://fly.io/install.ps1 -useb | iex
fly version
```

Authenticate and create the app:

```powershell
cd backend
fly auth login
fly apps create banksense-api
```

`banksense-api` must be globally unique. If it is taken, change `app` in
`backend/fly.toml`, create that name with `fly apps create`, and update
`VITE_API_BASE_URL` in Vercel to `https://<new-app-name>.fly.dev` before
deploying the frontend. Also update the health-check URLs in this guide and
`BANKSENSE_CORS_ORIGINS` in Step 5. Keep the region as `sin`.

Set the backend secrets (these are not stored in `fly.toml`):

```powershell
fly secrets set `
  SUPABASE_URL="https://<project-ref>.supabase.co" `
  SUPABASE_PUBLISHABLE_KEY="<publishable key from Supabase Project Settings -> API>"
```

Deploy:

```powershell
fly deploy
```

The first build takes a while: it installs CPU torch, installs the Python
requirements, and pre-fetches the SBERT encoder. Later deploys reuse cached
layers.

Verify the machine:

```powershell
fly status
fly logs
Invoke-RestMethod https://banksense-api.fly.dev/
```

`/` returns a small JSON document without loading the models, so it is used for
the Fly health check. Check the full health endpoint after the machine is up:

```powershell
Invoke-RestMethod https://banksense-api.fly.dev/api/health
```

The first `/api/health` call loads both classifiers and can take about 30
seconds. Expected: `status=ok`, `database=ok`, `auth=required`, both model flags
`true`, `summary=unavailable`.

> **CORS comes later.** Until Step 5 sets `BANKSENSE_CORS_ORIGINS` to the Vercel
> origin, browser requests from Vercel will be blocked. That is expected.

## Step 4 — Deploy the Vercel frontend (production)

From the repository root:

```powershell
npx vercel login
npx vercel link
```

Create a new project and keep the **Root Directory** as the repository root.
`vercel.json` already points the install/build/output at `frontend/`.

Add the production environment variables in **Vercel → Project → Settings →
Environment Variables** (add them to Production, and Preview if you use preview
deployments):

```env
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<same publishable key>
VITE_API_BASE_URL=https://banksense-api.fly.dev
```

`VITE_API_BASE_URL` is required and must be the Fly.io HTTPS origin, with no
trailing slash. If you renamed the Fly app, use the new
`https://<new-app-name>.fly.dev` origin here. The Vite config fails a Vercel
build if the value is missing, is not HTTPS, contains a path/query/hash, or
points at localhost, a loopback address, or a private/local hostname. This
prevents a misconfigured frontend from silently calling its own host or a local
machine. Local development is unchanged and still uses the Vite `/api` proxy.

Deploy:

```powershell
npx vercel deploy --prod
```

Note the production domain printed by the CLI, for example
`https://banksense.vercel.app`.

## Step 5 — Allow the Vercel origin in the backend (production)

Set the exact frontend origin (scheme included, no trailing slash):

```powershell
fly secrets set BANKSENSE_CORS_ORIGINS="https://<your-project>.vercel.app"
```

`fly secrets set` triggers a rolling restart. Add comma-separated origins only
if you also test from localhost or a fixed preview domain:

```text
https://<your-project>.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

Vercel preview URLs change per deployment. Either add each one you need or test
only the stable production domain.

## Step 6 — Configure Supabase and Google OAuth (production)

In the Supabase dashboard:

1. **Authentication → URL Configuration**
   - **Site URL:** your Vercel production domain, e.g.
     `https://banksense.vercel.app`
   - **Redirect URLs:** the same production domain, plus
     `http://localhost:5173` and `http://127.0.0.1:5173` for local testing.
2. **Authentication → Providers → Google**
   - Enable Google and set your own Client ID and Client Secret.
3. **Google Cloud Console → Credentials → OAuth client**
   - Authorized JavaScript origin: your production frontend origin.
   - Authorized redirect URI:
     `https://<project-ref>.supabase.co/auth/v1/callback`
4. **SQL Editor** — add the test Google account to the allowlist:

```sql
insert into public.allowed_users (email, note)
values ('<test-google-account-email>', 'hosting acceptance test')
on conflict (email) do nothing;
```

Existing allowlist rows must remain.

The frontend uses `window.location.origin` as the Supabase `redirectTo`, so the
production domain must be in the Supabase redirect allowlist.

## Step 7 — Acceptance checks

```text
[ ] Fly.io root URL returns the BankSense service document
[ ] GET /api/health returns status=ok, database=ok, auth=required
[ ] Both model flags are true and summary is unavailable
[ ] Frontend production build succeeds with VITE_API_BASE_URL set
[ ] Google sign-in works on the production domain
[ ] The test Google account is in public.allowed_users
[ ] Complaint submission returns 200
[ ] Dashboard loads analytics for the signed-in user
[ ] A second invited user cannot see the first user's complaints
[ ] An uninvited Google account gets 403 NOT_INVITED
[ ] No browser console CORS errors
[ ] No Supabase redirect_uri_mismatch errors
```

Quick checks from a terminal:

```powershell
Invoke-RestMethod https://banksense-api.fly.dev/api/health
fly logs
```

## Updating the deployment

| Change | Command |
|---|---|
| Backend code or models | `cd backend` then `fly deploy` |
| Backend secret | `fly secrets set NAME="value"` |
| Frontend code | `npx vercel deploy --prod` from the repository root |
| Frontend env value | Update it in Vercel, then redeploy |

A backend secret change or redeploy restarts the machine, so the first request
afterwards reloads the models.

## Security notes

- Model artifacts stay private: they are gitignored and baked into the Fly.io
  image, not uploaded to Vercel. `.vercelignore` excludes `backend/`.
- Never commit `.env` or the real Supabase keys.
- Use only the Supabase **publishable** key in the backend and frontend.
- Do **not** set `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_SECRET`, or `DATABASE_URL`
  in production. They are not needed for normal traffic and would weaken RLS.
- Keep `BANKSENSE_CORS_ORIGINS` restricted to the exact frontend origin.
- Fly secrets are encrypted at rest and are not written into `fly.toml`.
- The backend verifies the user's JWT through Supabase JWKS; RLS is always
  evaluated with that token.

## Troubleshooting

| Symptom | Check |
|---|---|
| `fly` command not found | Reinstall with the install script and reopen the terminal. |
| `fly deploy` fails at `test -f` | The five model files are missing or misnamed in `backend/models/`. |
| Fly app name already taken | Change `app` in `backend/fly.toml`, then `fly apps create <new-name>` and deploy. |
| Health check fails / `502` | The app must listen on `0.0.0.0:8080`. Check `fly logs`, `PORT`, and `internal_port` in `fly.toml`. |
| Machine restarts or is OOM-killed | Check `fly logs`; keep `BANKSENSE_ENABLE_SUMMARY=0` and the 2 GB machine size. |
| `503 MODEL_UNAVAILABLE` | Models are missing from the image or `BANKSENSE_MODELS_DIR` is wrong. Rebuild from a machine with `backend/models/`. |
| `summary: unavailable` | Expected with `BANKSENSE_ENABLE_SUMMARY=0`. |
| CORS error | `BANKSENSE_CORS_ORIGINS` must exactly match the frontend origin, including `https://` and no trailing slash. Re-run `fly secrets set` after changing it. |
| Frontend calls the wrong API | `VITE_API_BASE_URL` must be the Fly.io HTTPS origin. Fix it in Vercel and redeploy. |
| Vercel build: `VITE_API_BASE_URL is required` | Add the variable to the Production environment (and Preview if used), then redeploy. |
| `401 UNAUTHORIZED` | User is signed out or the access token expired. Check the Supabase URL/key and sign-in state. |
| `403 NOT_INVITED` | Add the Google email to `public.allowed_users`. |
| `redirect_uri_mismatch` | The Google redirect URI must be `https://<project-ref>.supabase.co/auth/v1/callback`. |
| First `/api/health` is slow | Expected: it loads both classifiers. The `/` check keeps the machine alive; later calls are fast. |
| Docker build drops during `pip install` | Retry. The Dockerfile sets pip retries and a 60-second timeout; this was a network issue, not a code error. |
| Vercel upload includes backend files | Confirm `.vercelignore` is at the repository root and the Vercel Root Directory is the repository root. |

## Why not the Vercel Services/Container Runtime beta?

The earlier version of this guide used Vercel beta Services and Container
Runtime to host both layers on one domain. That path is no longer used because:

- Both features are beta and their limits can change.
- The container scaled to zero, adding a 20–40 second cold start.
- Vercel's container registry and runtime limits added avoidable risk.

Fly.io keeps the same `backend/Dockerfile`, runs the container continuously, and
costs about $17/month for the approved 2 GB configuration.
