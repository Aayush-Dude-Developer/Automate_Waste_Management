# Automate_Waste_Management (SustainBite / Straits Garden Kitchen Ops)

AI-powered food waste management and inventory optimization application.

## 1. Project Structure

- `frontend/`: React 18, Vite, TypeScript, Tailwind CSS v4.
- `backend/`: FastAPI (Python), Google Cloud Firestore / Local Fallback, Gemini GenAI integrations.
- `docs/`: Comprehensive system architecture, schema, and API contracts.

The frontend pages now call the backend for inventory, analytics, planning,
waste, donations, handovers, and document-import APIs. Document OCR itself is
not implemented; uploads return an explicit empty preview instead of sample
extractions. Some backend donation matching data is still seeded/demo data.

## 2. Environment Setup

Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
For local development, leave `ENVIRONMENT=development`. Firebase sign-in is
not required in this mode; the frontend and backend allow local API requests
without Firebase credentials. Do not expose this development configuration as
a public service. Add `GEMINI_API_KEY` to enable Gemini features; without it,
the app uses the deterministic fallback.

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
# Activate virtual environment (Windows):
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
# source .venv/bin/activate
pip install -r requirements.txt

# Run the FastAPI server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
The API health check will be accessible at `http://localhost:8000/api/health`.
For Windows-specific Firestore credentials and run steps, see
[FRIEND_SETUP.md](./FRIEND_SETUP.md).

### Testing
To run the automated test suite for deterministic engines and API workflows:
```bash
cd backend
pytest
```

## Cloud Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the Cloud Run and Firebase Hosting setup.
