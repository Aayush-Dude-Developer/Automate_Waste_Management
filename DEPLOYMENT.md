# SustainBite Cloud Deployment

This is the runbook for the current Google Cloud Run + Firebase Hosting
deployment and for publishing later code changes. It covers the deployment
completed on October 11, 2026.

## Current deployment

- Google Cloud / Firebase project: `automate-511215` (`Automate`)
- Cloud Run API: `sustainbite-api`, region `asia-south1`
- API URL: <https://sustainbite-api-iecklamoxa-el.a.run.app>
- Firebase Hosting: <https://automate-511215.web.app>
- Firebase Web app: `SustainBite-Web`
- Cloud Run runtime service account:
  `sustainbite-runtime@automate-511215.iam.gserviceaccount.com`
- Firestore database: `default` (existing database)
- Workspace selected by the backend: `taiken_kharadi`
- Production sign-in: Firebase Authentication with Google; the backend
  allowlists the two owner-approved accounts through
  `ALLOWED_USER_EMAILS`.
- Cloud Run scaling: zero minimum instances and a two-instance maximum.
- Gemini: Cloud Run reads `GEMINI_API_KEY` from Secret Manager using the
  `latest` version alias. On October 11, 2026, version 2 was enabled after
  Gemini requests using the previous version failed with HTTP 402 because its
  prepayment credits were depleted. Subsequent investigation requests returned
  HTTP 200 without a logged Gemini failure; verify the investigation summary
  itself before treating that as proof that Gemini generated it.

The Firebase Hosting site is public, but application data endpoints require a
verified Firebase ID token and an allowlisted verified email. The browser does
not choose the restaurant workspace.

## What was set up

1. Linked the Google Cloud project to the active trial billing account. The
   trial page showed credit and an end date; check the Billing console for the
   current trial balance and terms.
2. Enabled the Cloud Run, Cloud Build, Artifact Registry, Secret Manager,
   Firestore, and Identity Platform APIs.
3. Created the `sustainbite-runtime` service account and granted
   `roles/datastore.user` for Firestore access. No service-account key file was
   created or uploaded.
4. Registered the existing Cloud project with Firebase, created the
   `SustainBite-Web` Firebase Web app, and enabled Google as an Authentication
   provider with the project support email.
5. Built the API from the repository Dockerfile, deployed it to Cloud Run with
   production auth settings, attached the runtime service account, and limited
   it to at most two instances.
6. Added the Firebase Web app settings to the local ignored file
   `frontend/.env.local`, built the frontend, then deployed it to Firebase
   Hosting. `frontend/.env.local` is ignored by Git.
7. Verified the Hosting page returned HTTP 200 and `/api/health` through the
   Hosting rewrite returned HTTP 401 without a token. The 401 is expected and
   confirms the endpoint requires authentication; it does not by itself prove
   Firestore reads or writes are succeeding.

The first Cloud Run `--source` deployment attempt failed because the source
buildpack did not find the FastAPI entrypoint under `backend/`. The successful
procedure below explicitly builds the root `Dockerfile` with `gcloud builds
submit`, then deploys that image.

## Prerequisites

- Google Cloud CLI (`gcloud`), Node.js/npm, and Firebase CLI (`firebase`).
- A Google account with permission to deploy in `automate-511215`, configure
  Firebase, and use the linked billing account.
- Billing linked to the Google Cloud project. A free trial or free-tier
  allowance does not guarantee that every service or all usage is free.
- The existing Firestore database and Google Authentication configuration.
- The Google account email(s) to allow in production.

Authenticate both CLIs as needed:

```powershell
gcloud auth login
gcloud config set project automate-511215
firebase login
firebase use automate-511215
```

For a headless Firebase CLI login, run `firebase login --no-localhost`, open
the exact URL it prints, sign in, verify the session ID on the page, then enter
the authorization code at the local PowerShell prompt. Never paste an
authorization code into chat, source control, or a project file.

## One-time Google Cloud setup

Enable the APIs (safe to repeat):

```powershell
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com firestore.googleapis.com identitytoolkit.googleapis.com --project automate-511215
```

The runtime identity and Firestore role already exist. If recreating the
environment, create/grant them with:

```powershell
gcloud iam service-accounts create sustainbite-runtime --project automate-511215 --display-name "SustainBite Cloud Run runtime"
gcloud projects add-iam-policy-binding automate-511215 --member="serviceAccount:sustainbite-runtime@automate-511215.iam.gserviceaccount.com" --role="roles/datastore.user"
```

Cloud Run uses its attached service account; do not download a service-account
JSON key.

## Firebase Authentication and frontend configuration

In Firebase Console for `automate-511215`:

1. Under **Authentication → Sign-in method**, confirm **Google** is enabled.
   The public project name and support email must be configured for the
   provider.
2. In Authentication settings, check that `automate-511215.web.app` is an
   authorized domain. Add it if missing.
3. Under **Project settings → General → Your apps**, use the `SustainBite-Web`
   app's web configuration.
4. On each developer's machine, copy the template and enter that Web app's
   public settings:

   ```powershell
   Set-Location .\frontend
   Copy-Item .env.example .env.local
   notepad .env.local
   ```

   Set `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`,
   `VITE_FIREBASE_PROJECT_ID`, and `VITE_FIREBASE_APP_ID`. These are client
   configuration values; do not put a Gemini API key in any `VITE_` variable.
   `frontend/.env.local` is ignored by Git.

The Firebase app configuration is public frontend configuration, not backend
authorization. Access is enforced by backend token verification and the
server-side email allowlist.

**Important repository note:** the root `.env` is excluded from Cloud Build
uploads by `.gcloudignore`, but it is already tracked in the repository's Git
history. Do not add secrets to it. `frontend/.env.local` is ignored by Git.
Review the existing root `.env` tracking separately before adding any secret
or creating another commit that changes that file.

## Deploy or update the backend

Run from the project root in PowerShell. The Dockerfile installs only
`backend/requirements.txt` and runs the FastAPI app on Cloud Run's `$PORT`.
`.gcloudignore` excludes local environment files, virtual environments,
dependencies, caches, and build output from the uploaded source.

First build the image:

```powershell
gcloud builds submit --project automate-511215 --region asia-south1 --tag asia-south1-docker.pkg.dev/automate-511215/cloud-run-source-deploy/sustainbite-api:latest --ignore-file .gcloudignore .
```

Then deploy it. This example uses the approved account allowlist for the
current deployment. Change it only to add/remove explicitly authorized
verified Google accounts.

```powershell
$envVars = @{
  ENVIRONMENT = "production"
  DATABASE_BACKEND = "firestore"
  GOOGLE_CLOUD_PROJECT = "automate-511215"
  GEMINI_MODEL = "gemini-3.8-flash"
  DEFAULT_RESTAURANT_ID = "taiken_kharadi"
  ALLOWED_USER_EMAILS = "owner@example.com,friend@example.com"
}
$envFile = Join-Path $env:TEMP "sustainbite-cloudrun-env.json"
try {
  $envVars | ConvertTo-Json | Set-Content -Path $envFile -Encoding utf8
  gcloud run deploy sustainbite-api `
    --image asia-south1-docker.pkg.dev/automate-511215/cloud-run-source-deploy/sustainbite-api:latest `
    --project automate-511215 `
    --region asia-south1 `
    --service-account sustainbite-runtime@automate-511215.iam.gserviceaccount.com `
    --allow-unauthenticated `
    --max-instances 2 `
    --min-instances 0 `
    --env-vars-file $envFile
} finally {
  Remove-Item -LiteralPath $envFile -ErrorAction SilentlyContinue
}
```

Replace the example emails with the actual owner-approved addresses. The
temporary JSON file contains non-secret deployment settings, is written
outside the repository, and is removed after the command. Do not deploy with
an empty allowlist or `ENVIRONMENT=development`.

`--allow-unauthenticated` permits Firebase Hosting's rewrite to reach Cloud
Run; the API still enforces Firebase ID tokens. Keep the `sustainbite-api`
service name and `asia-south1` region because `firebase.json` points to them.
Cloud Run gives this service a generated URL; Hosting forwards `/api/**` to it.

### Optional Gemini key

Without a key, the application uses deterministic fallback behavior. To enable
Gemini, create a Secret Manager secret named `GEMINI_API_KEY` in project
`automate-511215`, add the key as a secret version through the Google Cloud
Console, and grant the runtime account access:

```powershell
gcloud secrets add-iam-policy-binding GEMINI_API_KEY --project=automate-511215 --member="serviceAccount:sustainbite-runtime@automate-511215.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

Then add this flag to the `gcloud run deploy` command:

```powershell
--set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

Do not put the key in this guide, `.env`, Git, a frontend variable, or a command
line that will be saved in shell history.

### Rotate or update the Gemini key

When changing keys, create a **new version** of the existing
`GEMINI_API_KEY` secret in Secret Manager and leave the key value out of chat,
source files, and shell command history. Confirm that the new key belongs to a
Google AI Studio project that is allowed to use the configured model and has
available Gemini API billing/credits. A new key in the same project does not
restore depleted project or billing-account credits.

Cloud Run is configured to use the `latest` secret version. For environment
variable secrets, Cloud Run resolves that alias when an instance starts, so
existing instances may still have the prior value. Create a new revision that
retains the `latest` secret reference to make instances restart on the new
version:

```powershell
gcloud run services update sustainbite-api `
  --project automate-511215 `
  --region asia-south1 `
  --update-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

Check only the secret reference and revision metadata; do not print or retrieve
the secret value:

```powershell
$service = gcloud run services describe sustainbite-api `
  --project automate-511215 `
  --region asia-south1 `
  --format=json | ConvertFrom-Json
$service.status.latestReadyRevisionName
$service.spec.template.spec.containers |
  ForEach-Object {
    $_.env |
      Where-Object { $_.name -eq "GEMINI_API_KEY" } |
      ForEach-Object {
        "Secret: $($_.valueFrom.secretKeyRef.name), version: $($_.valueFrom.secretKeyRef.key)"
      }
  }
```

### Debug Gemini and API errors

Use **Surplus & Waste → Analyze Risk** on an existing waste entry linked to an
inventory item. The request may consume Gemini API quota. Inspect the
Investigation result:

- A summary beginning `Automated risk analysis for` is the deterministic
  fallback, not a Gemini-generated result.
- A different summary is a useful signal, but verify the request logs for the
  same time as well; the endpoint can return HTTP 200 even when Gemini fails
  and the backend falls back.

Read recent Cloud Run logs without exposing the secret:

```powershell
$filter = "resource.type=cloud_run_revision AND resource.labels.service_name=sustainbite-api AND textPayload:Gemini"
gcloud logging read $filter `
  --project automate-511215 `
  --limit 20 `
  --format "value(timestamp,severity,textPayload)"
```

The backend logs Gemini failures with `Gemini API failed`. An HTTP 402 with a
message about depleted prepayment credits means the API key was accepted far
enough to reach Gemini, but its AI Studio project/billing account has no
available prepay balance; generating another key for that same project will
not fix it. Check **Google AI Studio → Projects** for its Billing Tier/Status
and **Dashboard → Usage**. Google Cloud trial credit and Google Cloud Billing
budgets do not top up Gemini API prepay credit. If choosing not to pay, leave
the secret as-is; the app's fallback remains available.

For a 502 from Firebase Hosting or the API:

1. Retry after a short wait; a 502 can be a transient gateway failure.
2. Check that the Cloud Run service has a ready revision and read the recent
   Cloud Run request logs. A 401 from an unauthenticated `/api/health` request
   is expected; test app routes while signed in.
3. If Cloud Run has no matching failed request, check Hosting's `/api/**`
   rewrite and the service name/region in `firebase.json`. A browser extension
   console warning is not by itself evidence of an API failure.

Do not paste `.env` files, OAuth authorization codes, API keys, or secret
values into logs, screenshots, or chat.

## Build and deploy or update Firebase Hosting

The Firebase config is needed before building because Vite embeds these public
settings in the generated static assets.

```powershell
Set-Location .\frontend
npm ci
npm run build
Set-Location ..
firebase deploy --only hosting --project automate-511215
```

Hosting serves `frontend/dist`, rewrites `/api/**` to Cloud Run, and sends
other paths to `index.html` for React Router. Redeploy Hosting after changing
frontend code or Firebase Web app settings; redeploy Cloud Run after backend
code or backend configuration changes.

## Verify the deployment

1. Open <https://automate-511215.web.app> and confirm the SustainBite sign-in
   screen loads.
2. Sign in with an authorized Google account. If Google reports
   `auth/unauthorized-domain`, add `automate-511215.web.app` under Firebase
   Authentication's authorized domains.
3. Confirm the app loads its dashboard and API data. In **Settings**, review
   the backend status. Health status alone is not proof of Firestore operations.
4. An unauthenticated check should be rejected with 401:

   ```powershell
   Invoke-WebRequest https://automate-511215.web.app/api/health
   ```

   PowerShell may show the 401 as a `WebException`; that is expected without a
   Firebase sign-in token.
5. Check the Cloud Run service and current instance cap:

   ```powershell
   gcloud run services describe sustainbite-api --project automate-511215 --region asia-south1
   ```

## Costs and shutdown behavior

The current service has zero minimum instances and a maximum of two, with
1 vCPU and 512 MiB memory per instance. This constrains scaling and allows
scale-to-zero; it is **not** a spending limit. Cloud Run, builds, Artifact
Registry storage, Firestore, logging, network traffic, and optional Gemini
usage may incur costs, subject to current free-tier/trial allowances.

At the last check, the billing page showed an account-wide ₹100 monthly
**alerts-only** budget at 50%, 90%, 100%, and 150%; its spend-cap status was
“Not applicable.” It does not stop charges and is not project-specific. A
Cloud Billing budget is not a hard cap unless an enforced spend cap is
explicitly available, configured, and shown as active for the applicable
project/services. Check the Billing console rather than assuming a cap exists.

The Free Trial page previously showed credit remaining and an end date of
January 10, 2027. Google stated trial resources stop at trial end unless the
account is upgraded. Recheck trial status, current credits, billing terms, and
cost reports in the console; balances and eligibility can change. Set suitable
alerts and inspect usage regularly. Budget alerts can arrive late because
usage reporting is delayed.

## Security and known limitations

- Cloud source uploads exclude the root `.env` and `frontend/.env.local`.
  `frontend/.env.local` is ignored by Git, but the root `.env` is already
  tracked in Git history; never place secrets in it.
- All allowlisted accounts currently share the one configured restaurant
  workspace; user-specific/multi-tenant workspaces are not implemented.
- Local development auth bypass is enabled only when the backend environment
  is `development`. Production must remain `ENVIRONMENT=production`.
- Document OCR is not implemented. Donation matching may include seeded demo
  centres unless AI discovery is enabled. Verify donation organizations
  independently.
