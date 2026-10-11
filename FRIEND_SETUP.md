# Local setup for Windows

This project has a FastAPI backend and a Vite frontend. Most operational
screens call the backend API. Document OCR is not implemented, and donation
matching still uses seeded centres unless AI discovery is enabled.

## Requirements

- Python 3.12
- Node.js and npm
- Google Cloud CLI (`gcloud`)
- Access to the `automate-511215` Google Cloud project

## Configure local credentials

The root `.env` contains the local backend settings. When `ENVIRONMENT` is
`development` (the default), you can run locally without configuring Firebase
sign-in. This development-only mode is intended for a backend bound to
`127.0.0.1`; do not use it for a public deployment.

The backend currently uses Firestore, so ask the project administrator to grant
your Google account Firestore access (the Cloud Datastore User role is
sufficient for normal read/write testing). Sign in with Application Default
Credentials:

   ```powershell
   gcloud auth application-default login
   ```

To test Google sign-in locally, configure a Firebase web app and Google
Authentication provider, put its public web settings in `frontend/.env.local`
(see `frontend/.env.example`), and set your account in `ALLOWED_USER_EMAILS`.
Otherwise, leave Firebase web settings unconfigured for local development.

Create a Gemini API key in Google AI Studio. Put it in the root `.env` as
`GEMINI_API_KEY=your_new_key`, replacing the placeholder/empty value. Keep the
key private and do not stage or commit `.env` after adding it.

The backend loads the root `.env` when launched from the `backend` directory.
The configured Gemini model is `gemini-3.8-flash`.

## Start the backend

In PowerShell, from the project root:

```powershell
Set-Location .\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir .. --reload --host 127.0.0.1 --port 8000
```

If the virtual environment already exists, skip the `venv` creation line.
Swagger is at <http://127.0.0.1:8000/docs>.

## Start the frontend

Open a second PowerShell terminal at the project root:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open the local URL printed by Vite, normally <http://localhost:5173>. With
Firebase unconfigured and `ENVIRONMENT=development`, the local app opens
without signing in. Vite proxies `/api` requests to the backend on port 8000;
start the backend first.

## Test

- Create an inventory item with `POST /api/inventory/items`.
- Add an item in the Inventory screen. Log waste against an inventory item to
  update stock and make it available for investigation.
- Use Analyze Risk on an associated waste record to call Gemini or the
  deterministic backend fallback.
- A Gemini investigation should contain data-specific analysis; check the backend
  terminal for `Gemini API failed:` if the request falls back.
- `POST /api/ai/investigations/{investigation_id}/approve-action` records approval
  only; it does not change inventory.
- Donation matching currently relies on seeded demo centres unless `use_ai=true`.
  Verify any returned organization independently. Handover records are saved;
  they do not arrange a real pickup.
- Document uploads are accepted but automatic OCR is not implemented. Uploads
  therefore produce no extracted sample records; confirmed JSON records can be
  imported manually.

The standalone Gemini check can be run from the `backend` directory with:

```powershell
.\.venv\Scripts\python.exe check_gemini.py
```
