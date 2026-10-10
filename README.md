# Automate_Waste_Management (SustainBite / Taiken Ops)

AI-powered food waste management and inventory optimization application.

## 1. Project Structure

- `frontend/`: React 18, Vite, TypeScript, Tailwind CSS v4.
- `backend/`: FastAPI (Python), Google Cloud Firestore / Local Fallback, Gemini GenAI integrations.
- `docs/`: Comprehensive system architecture, schema, and API contracts.

## 2. Environment Setup

Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
Ensure your `GEMINI_API_KEY` is added to enable AI Agent features. If not added, the app will fall back to deterministic mode.

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

### Testing
To run the automated test suite for deterministic engines and API workflows:
```bash
cd backend
pytest
```
