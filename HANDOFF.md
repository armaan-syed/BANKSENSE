# BankSense hosting handoff

This document is the deployment handoff for Person A (Fahad). The application is
already implemented and connected to Supabase. The remaining work is to host the
React frontend and FastAPI backend, configure production URLs, and pass the
acceptance checks below.

## Ownership and access

- **Owner:** Armaan. Retains access to GitHub, Supabase, Google Cloud, the
  domain, and billing. **Do not remove or downgrade Armaan's access.**
- **Hosting owner:** Fahad (`fahadsyed2705@gmail.com`).
- **GitHub:** `https://github.com/armaan-syed/BANKSENSE`, branch `armaan`.
- **Supabase project:** `https://mndrufddugbqigpubgxf.supabase.co`.
- **Supabase role:** Fahad has Administrator. Armaan remains Owner.
- **Google OAuth:** Fahad will create and own a separate Google OAuth client.
  Armaan's Google Cloud project is not changed.
- **Domain/DNS:** Fahad chooses the production domain. If a custom domain is
  used, Armaan retains domain ownership and delegates DNS access to Fahad.

Do not transfer ownership. Do not remove Armaan from GitHub, Supabase, Google
Cloud, domain, or billing.

## What is in this branch

Included:

- FastAPI backend with Supabase Auth/JWT verification and per-user RLS
- React/Vite frontend with Google sign-in
- Supabase schema, RLS policies, and allowlist
- SQLite fallback for local development
- Model training/evaluation code and reports
- Runtime documentation and environment template

Excluded from Git:

- `.env` (contains secrets; never commit)
- `backend/models/` (provided separately as `model.zip`)
- `frontend/node_modules/`
- `frontend/dist/`
- local SQLite database and raw datasets

Development test suites and local planning notes were removed from this handoff
branch to keep it deployment-focused. They are not required to host the app.

## Required model files

`model.zip` must contain these files under `backend/models/`:

```text
backend/models/tfidf_logreg.joblib
backend/models/sbert_logreg.joblib
backend/models/label_classes.json
backend/models/sbert_model_name.txt
backend/models/training_metadata.json
```

Place them in `backend/models/` before starting the backend. If the host mounts
models elsewhere, set `BANKSENSE_MODELS_DIR`.

The SBERT encoder downloads `sentence-transformers/all-MiniLM-L6-v2` (about
90 MB) from Hugging Face on first use. The optional summariser downloads
`sshleifer/distilbart-cnn-12-6` (about 1.2 GB) only when a long complaint is
summarised. Allow outbound network access and sufficient disk space, or pre-warm
the models during the deployment build.

## Supabase configuration

The project already has:

- `public.complaints` with per-user RLS
- `public.allowed_users` invite allowlist
- Google sign-in enabled
- A production-ready schema and grants

Fahad can read the project URL and publishable key from
**Project Settings → API**.

### Production URLs

In **Authentication → URL Configuration**:

- **Site URL:** final production frontend URL, e.g.
  `https://banksense.example.com`
- **Redirect URLs:**
  - `https://banksense.example.com`
  - `http://localhost:5173` (optional for local testing)
  - `http://127.0.0.1:5173` (optional for local testing)

### Allowlist

Add Fahad's Google account for testing:

```sql
insert into public.allowed_users (email, note)
values ('fahadsyed2705@gmail.com', 'hosting acceptance test')
on conflict (email) do nothing;
```

Armaan's existing allowlist row must remain. Uninvited Google accounts may
authenticate but the API returns `403 NOT_INVITED` and RLS blocks their data.

### Existing test data

There is currently one test complaint in Supabase. Remove it if a clean
production dataset is preferred:

```sql
delete from public.complaints where id = 6;
```

## Google OAuth setup for Fahad

Use Fahad's own Google Cloud project. Do not modify Armaan's Google Cloud
project unless Armaan asks.

1. Open <https://console.cloud.google.com/> and create a project.
2. Configure **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - App name: `BankSense`
   - Add support email and developer contact
   - Scopes: `openid`, `email`, `profile`
   - If the app remains in **Testing**, add each allowed Google account as a
     test user. Publish the app for general use.
3. Create **Credentials → OAuth client ID → Web application**.
4. Add **Authorized JavaScript origins**:
   - `http://localhost:5173` for local testing
   - the final production frontend origin
5. Add **Authorized redirect URI** exactly:

```text
https://mndrufddugbqigpubgxf.supabase.co/auth/v1/callback
```

The frontend URL is not the redirect URI. Google returns to Supabase, and
Supabase returns to the frontend.

6. Copy the Client ID and Client Secret.
7. In Supabase go to **Authentication → Providers → Google**.
8. Enable Google and replace the existing Client ID/Secret with Fahad's values.
9. Save and test.

Do not put the Google Client Secret in the frontend or in `.env`. It belongs
only in the Supabase provider settings.

### Existing Google identity caveat

A new Google OAuth client can produce a new Supabase identity for existing
Google users. The email allowlist still works, but data owned by the old
Supabase user ID, such as the existing test complaint, may no longer be visible
to that account. If preserving existing user-linked data is important, use the
existing Google OAuth client instead of creating a new one.

## Backend deployment

### Requirements

- Python 3.10+
- CPU PyTorch (do not install the CUDA wheel on CPU hosts)
- 2 GB+ RAM recommended for SBERT
- Long-running container or VM; do not use a standard Vercel Python function
- Outbound internet access for Hugging Face model downloads

### Environment variables

```env
BANKSENSE_DB_BACKEND=supabase
SUPABASE_URL=https://mndrufddugbqigpubgxf.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable key from Supabase dashboard>
BANKSENSE_CORS_ORIGINS=https://<production-frontend-origin>
```

Optional:

```env
BANKSENSE_MODELS_DIR=/app/backend/models
BANKSENSE_SBERT_MODEL=sentence-transformers/all-MiniLM-L6-v2
BANKSENSE_SUMMARY_MODEL=sshleifer/distilbart-cnn-12-6
```

Do **not** set `DATABASE_URL`, `SUPABASE_SECRET_KEY`, or
`SUPABASE_JWT_SECRET` in production. They are not needed for normal application
traffic. The backend uses the user's JWT so Supabase RLS is enforced.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
```

### Start

Run from the repository root so `backend.*` imports resolve:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Health check:

```text
GET /api/health
```

Expected:

```json
{
  "status": "ok",
  "models": {"tfidf": true, "sbert": true},
  "summary": "enabled",
  "database": "ok",
  "auth": "required"
}
```

`summary` may be `unavailable` if the optional summariser stack is omitted. The
core complaint flow still works.

## Frontend deployment

Build the static site:

```bash
cd frontend
npm ci
npm run build
```

Deploy `frontend/dist` to Vercel, Netlify, Cloudflare Pages, or any static host.

### Build-time environment variables

```env
VITE_SUPABASE_URL=https://mndrufddugbqigpubgxf.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<same publishable key>
VITE_API_BASE_URL=https://<production-backend-origin>
```

`VITE_API_BASE_URL` must be set at build time. If it is blank, the frontend uses
the Vite development proxy and production will call the frontend host instead of
the backend.

The Vite config also falls back to `SUPABASE_URL` and
`SUPABASE_PUBLISHABLE_KEY` from the repository-root `.env` or host environment.

## CORS

Set `BANKSENSE_CORS_ORIGINS` to the exact frontend origin, with scheme and no
trailing slash:

```env
BANKSENSE_CORS_ORIGINS=https://banksense.example.com
```

If testing locally, include:

```env
BANKSENSE_CORS_ORIGINS=https://banksense.example.com,http://localhost:5173,http://127.0.0.1:5173
```

## Acceptance checklist

```text
[ ] Backend health returns status=ok, database=ok, auth=required
[ ] Frontend production build succeeds
[ ] Google sign-in works on the production domain
[ ] Fahad's Google account is in public.allowed_users
[ ] Complaint submission returns 200
[ ] Dashboard loads analytics for the signed-in user
[ ] A second invited user cannot see the first user's complaints
[ ] An uninvited Google account gets 403 NOT_INVITED
[ ] No browser console CORS errors
[ ] No Supabase redirect_uri_mismatch errors
```

## Troubleshooting

| Symptom | Check |
|---|---|
| `401 UNAUTHORIZED` | User is signed out or the access token expired. Check Supabase URL/key and sign-in state. |
| `403 NOT_INVITED` | Add the Google email to `public.allowed_users`. |
| `503 MODEL_UNAVAILABLE` | Confirm the five model files are in `backend/models/` or set `BANKSENSE_MODELS_DIR`. |
| CORS error | `BANKSENSE_CORS_ORIGINS` must exactly match the frontend origin. |
| `redirect_uri_mismatch` | Google redirect URI must be `https://mndrufddugbqigpubgxf.supabase.co/auth/v1/callback`. |
| Frontend calls wrong API | Set `VITE_API_BASE_URL` before running `npm run build`. |
| Google login blocked | If the OAuth app is in Testing, add the account as a test user or publish the app. |
| Old complaint missing | A new Google OAuth client may create a new Supabase identity; data is tied to the old user ID. |

## Handoff boundary

Fahad owns deployment, hosting configuration, and production operations. Armaan
retains ownership and access to GitHub, Supabase, Google Cloud, domain, and
billing. No access is to be removed.

For access or billing changes, coordinate with Armaan. For deployment issues,
Fahad can use the Supabase Administrator and GitHub collaborator access already
granted.
