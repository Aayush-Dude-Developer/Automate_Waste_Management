# Local setup for Windows

This project has a FastAPI backend and a Vite frontend. The frontend is currently
a demo and is not wired to the backend API; use Swagger to test the live backend.

## Requirements

- Python 3.12
- Node.js and npm
- Google Cloud CLI (`gcloud`)
- Access to the `automate-511215` Google Cloud project

## Configure credentials

The root `.env` contains the non-secret Firestore settings for project
`automate-511215` and database `default`. Do not commit API keys or credentials.

1. Ask the project administrator to grant your Google account Firestore access
   (the Cloud Datastore User role is sufficient for normal read/write testing).
2. Sign in with Application Default Credentials:

   ```powershell
   gcloud auth application-default login
   ```

3. Create a Gemini API key in Google AI Studio. Put it in the root `.env` as
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
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite, normally <http://localhost:5173>.

## Test

- Create an inventory item with `POST /api/inventory/items`.
- Use its returned ID with `POST /api/ai/investigate-surplus`.
- A Gemini investigation should contain data-specific analysis; check the backend
  terminal for `Gemini API failed:` if the request falls back.
- `POST /api/ai/investigations/{investigation_id}/approve-action` records approval
  only; it does not change inventory.
- Donation matching returns demo centres unless `use_ai=true`. Handover records
  a test handover; it does not arrange a real pickup.

The standalone Gemini check can be run from the `backend` directory with:

```powershell
.\.venv\Scripts\python.exe check_gemini.py
```
