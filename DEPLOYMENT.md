# Cloud deployment

This guide prepares the project for Google Cloud Run (FastAPI) and Firebase
Hosting (Vite). It targets `automate-511215` and deploys the backend in
`asia-south1`, near its Firestore database.

## Current feature limitations

Document OCR is not implemented, and donation matching includes seeded demo
centres unless AI discovery is enabled. Surplus investigations can use a
deterministic fallback when Gemini is unavailable.

## Prerequisites

- Billing enabled for `automate-511215`.
- Google Cloud CLI (`gcloud`), Node.js/npm, and Firebase CLI installed.
- Permission to enable APIs, create a service account and Cloud Run service,
  and configure Firebase Hosting.
- Firebase Authentication configured with the Google provider and a registered
  web app.
- Existing Firestore database (`default`) and a Gemini API key.

Cloud Run and other Google Cloud services can incur charges. The Cloud Run
service accepts network requests so Firebase Hosting can proxy them, but every
API endpoint verifies a Firebase ID token. The signed-in email must be in the
server-side `ALLOWED_USER_EMAILS` allowlist. The server—not the browser—selects
the restaurant workspace.

## 1. Select the project and enable services

In PowerShell, from the project root:

```powershell
gcloud auth login
gcloud config set project automate-511215
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com firestore.googleapis.com identitytoolkit.googleapis.com
```

Compute Engine is not required just to run this app on Cloud Run.

## 2. Give the backend a runtime identity

Create a dedicated service account and grant it Firestore access:

```powershell
gcloud iam service-accounts create sustainbite-runtime --display-name "SustainBite Cloud Run runtime"
gcloud projects add-iam-policy-binding automate-511215 --member="serviceAccount:sustainbite-runtime@automate-511215.iam.gserviceaccount.com" --role="roles/datastore.user"
```

Do not download or create a service-account key file. Cloud Run provides
credentials to the attached service account.

## 3. (Optional) Store the Gemini key in Secret Manager

Without a Gemini key, the app uses deterministic recommendations. If Gemini is
needed, create a secret named `GEMINI_API_KEY` in Secret Manager and add its
value as a secret version through the Google Cloud Console. Do not put the
Gemini key in this repository, a frontend `VITE_` variable, or a command saved
in shell history.

Allow the runtime service account to read the secret:

```powershell
gcloud secrets add-iam-policy-binding GEMINI_API_KEY --project=automate-511215 --member="serviceAccount:sustainbite-runtime@automate-511215.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

## 4. Configure Firebase Authentication

In the Firebase Console for `automate-511215`:

1. Register a Firebase Web app and copy its web configuration.
2. Under Authentication, enable the Google provider and add the Hosting domain
   to its authorized domains.
3. In `frontend`, copy `.env.example` to `.env.local` and fill in
   `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`,
   `VITE_FIREBASE_PROJECT_ID`, and `VITE_FIREBASE_APP_ID`.
   These are public Firebase client settings, not server credentials. Never
   put the Gemini key here.
4. Choose the verified Google accounts that may sign in. The backend uses
   `ALLOWED_USER_EMAILS`, a comma-separated email allowlist. Allowed users share
   the one `DEFAULT_RESTAURANT_ID` workspace.

## 5. Deploy the backend

From the project root:

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
$envVars | ConvertTo-Json | Set-Content -Path $envFile -Encoding utf8
gcloud builds submit --project automate-511215 --region asia-south1 --tag asia-south1-docker.pkg.dev/automate-511215/cloud-run-source-deploy/sustainbite-api:latest --ignore-file .gcloudignore .
gcloud run deploy sustainbite-api --image asia-south1-docker.pkg.dev/automate-511215/cloud-run-source-deploy/sustainbite-api:latest --project automate-511215 --region asia-south1 --service-account sustainbite-runtime@automate-511215.iam.gserviceaccount.com --allow-unauthenticated --max 2 --min 0 --env-vars-file $envFile
Remove-Item $envFile
```

If you created the optional Gemini secret, add
`--set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"` to the deploy command.

Replace the example email addresses with the exact Google accounts authorized
to use the app. Do not deploy with an empty allowlist. Cloud Run's
`--allow-unauthenticated` setting allows the Firebase Hosting proxy to reach the
service; it does not bypass the application's Firebase token verification and
email allowlist.

Keep the service name and region as `sustainbite-api` and `asia-south1`, since
`firebase.json` uses those values for its API rewrite. Check the deployed
service's `/docs` after deployment. The health endpoint also requires an
authorized Firebase sign-in and reports configuration, not successful live
Firestore/Gemini operations.

## 6. Build and deploy the frontend

Ensure `frontend/.env.local` contains the Firebase Web app settings before the
build. These public values are included in the built static site.

```powershell
Set-Location .\frontend
npm ci
npm run build
Set-Location ..
firebase login
firebase use automate-511215
firebase deploy --only hosting
```

If Firebase Hosting is not enabled for the project, enable it in the Firebase
Console first. Hosting rewrites `/api/**` to Cloud Run and sends other paths to
`index.html` for React Router.

## Credentials and access

The root `.env` and `frontend/.env.local` are excluded by `.dockerignore` and
`.gcloudignore`. Keep credentials out of Git regardless. Cloud Run uses its
attached service account for Firestore; no local ADC file is deployed. Firebase
Hosting is public, but using the app requires Google sign-in with an
allowlisted account. The backend maps all allowed users to the configured
single restaurant workspace, ignoring any restaurant ID supplied by a client.
