# Automate_Waste_Management (SustainBite / Straits Garden Kitchen Ops)

AI-powered food waste management and inventory optimization application.

## 1. Project Structure

- `frontend/`: React 18, Vite, TypeScript, Tailwind CSS v4.
- `backend/`: FastAPI (Python), Google Cloud Firestore / Local Fallback, Gemini GenAI integrations.
- `docs/`: Comprehensive system architecture, schema, and API contracts.

The frontend pages now call the backend for inventory, analytics, planning,
waste, donations, handovers, and document-import APIs. The configured sample
restaurant profile is Straits Garden Kitchen in Kharadi, Pune, India.
Seeded/generated operational records are explicitly marked as synthetic sample
data and shown with a notice in the application; they are not verified live
restaurant records. Document uploads use
Gemini to extract a reviewable preview from supported PDF, image, CSV, and text
files; imports are only written after explicit confirmation. Document
extraction requires `GEMINI_API_KEY`; if Gemini is temporarily unavailable,
the upload reports that the document was not extracted and can be retried.
Some backend donation matching data is still seeded/demo data.

## 2. Environment Setup

Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
For local development, leave `ENVIRONMENT=development`. Firebase sign-in is
not required in this mode; the frontend and backend allow local API requests
without Firebase credentials. Do not expose this development configuration as
a public service. Add `GEMINI_API_KEY` to enable Gemini features. Document
uploads return a clear configuration error when the key is missing.

The backend is configured to use the shared Firestore project. Each developer
must have Google Cloud access to that project and run
`gcloud auth application-default login` locally. The code does not grant
Firestore access by itself.

## 3. Running the Application

### Frontend (Development)
```bash
cd frontend
npm install
npm run dev
```
The application will be accessible at `http://localhost:5173`.

### Backend (Development)
Ensure Python 3.11+ is installed.
```bash
cd backend
python -m venv .venv
# Windows PowerShell: use the venv Python directly; activation may be blocked
# by the PowerShell execution policy.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Mac/Linux:
# source .venv/bin/activate
# pip install -r requirements.txt

# Run the FastAPI server (Windows PowerShell):
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir .. --reload --host 127.0.0.1 --port 8000
# Mac/Linux (with the virtual environment activated):
# uvicorn backend.main:app --app-dir .. --reload --host 127.0.0.1 --port 8000
```
The API health check will be accessible at `http://localhost:8000/api/health`.
For Windows-specific Firestore credentials and run steps, see
[FRIEND_SETUP.md](./FRIEND_SETUP.md).

### Testing
To run the automated test suite for deterministic engines and API workflows:
```bash
cd backend
# Windows PowerShell:
.\.venv\Scripts\python.exe -m pytest
# Mac/Linux (with the virtual environment activated):
# pytest
```

## Cloud Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the Cloud Run and Firebase Hosting setup.
