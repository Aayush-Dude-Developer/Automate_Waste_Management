# SustainBite / Taiken Ops — Agent & Developer Handoff Context

Welcome to the **SustainBite / Taiken Ops** codebase. This document is specifically structured for **Antigravity AI agents** and software engineers picking up this repository for testing, verification, bug fixes, and deployment.

---

## 1. Executive Summary & Core Mandate

* **Domain**: Food Waste Management, Inventory Optimization, and Surplus Prepared Food Recovery for Restaurants (pilot target: Pan-Asian restaurant *Taiken*, Kharadi / Culinary Divergence Pvt. Ltd.).
* **Key Architecture Rule**: **Strict separation of Deterministic Math vs. Generative AI Reasoning**.
  * Arithmetic, reorder thresholds (EOQ), inventory balances, yield percentages, batch sizing, and distance formulas are implemented in **pure Python**.
  * **Gemini 2.5** is used *only* for:
    1. Multimodal OCR/document extraction from unstructured restaurant sheets.
    2. Contextual root-cause investigation of surplus risk via backend tool calling.
    3. Donation-centre suggestions from Gemini's existing knowledge (without live grounding).

---

## 2. Repository Structure

```
Automate_Waste_Management/
├── .env.example                  # Environment template (GEMINI_API_KEY, Firestore toggle)
├── docs/                         # Formal design contracts & specifications
│   ├── PRODUCT_SPEC.md           # Business workflows, user roles, core questions
│   ├── ARCHITECTURE.md           # Separation of concerns & sequence flows
│   ├── DATABASE_SCHEMA.md        # Firestore collection contracts & tenant isolation
│   ├── API_SPEC.md               # REST endpoints, headers, payload models
│   ├── AI_AGENT_DESIGN.md        # Gemini system prompts, tool interfaces, approval gates
│   └── TEST_PLAN.md              # Test matrix & edge cases
├── backend/                      # FastAPI Python Application
│   ├── main.py                   # App entrypoint & CORS middleware
│   ├── config.py                 # Pydantic BaseSettings (.env loader)
│   ├── requirements.txt          # Dependencies (FastAPI, pydantic, google-genai, google-cloud-firestore)
│   ├── routers/                  # HTTP route handlers
│   │   ├── health.py             # GET /api/health
│   │   ├── inventory.py          # GET/POST /api/inventory/items & /movements
│   │   ├── waste.py              # POST /api/waste & /api/staff-meals
│   │   ├── planning.py           # POST /api/planning/replenishment & /buffet
│   │   ├── ai.py                 # POST /api/ai/investigate-surplus & /approve-action
│   │   ├── donations.py          # POST /api/donations/search & /handover
│   │   ├── documents.py          # POST /api/documents/upload & /confirm-import
│   │   └── analytics.py          # GET /api/analytics/dashboard
│   ├── engines/                  # Deterministic mathematical models (NO AI)
│   │   ├── forecasting_engine.py # EOQ & replenishment calculations
│   │   └── buffet_engine.py      # Batch-size yield calculations
│   ├── agents/                   # Generative AI agents & orchestrators
│   │   ├── investigation_agent.py# Gemini agent for root-cause analysis
│   │   └── tools.py              # Controlled backend tools callable by Gemini
│   ├── services/                 # Business logic & repository glue
│   ├── repositories/
│   │   └── database.py           # Dual-mode DB: Live Firestore with local JSON fallback
│   └── tests/
│       ├── test_health.py        # API health check test
│       └── test_engines.py       # Deterministic numerical assertions
└── frontend/                     # React 19 + TypeScript + Vite + Tailwind CSS v4
    ├── src/
    │   ├── App.tsx               # Browser router & view wiring
    │   ├── index.css             # Tailwind v4 import & custom theme tokens
    │   ├── components/
    │   │   └── Layout.tsx        # Responsive navigation shell with "Demo Mode" tag
    │   └── views/
    │       ├── DashboardView.tsx       # Recharts 7-day waste trends & KPIs
    │       ├── InventoryView.tsx       # Stock list & movement actions
    │       ├── SalesPurchasesView.tsx  # Restocking recommendations & pack-size advice
    │       ├── BuffetPlanningView.tsx  # Batch schedule & predicted surplus calculator
    │       ├── SurplusWasteView.tsx    # Waste logs & Agentic AI investigation panel
    │       ├── DonationCentresView.tsx # Multi-criteria matching & Gemini live discovery
    │       ├── DocumentsView.tsx       # Drag-and-drop document upload & OCR preview
    │       ├── ImpactReportsView.tsx   # Detailed sustainability reports stub
    │       └── SettingsView.tsx        # Profile & configuration view
    └── package.json
```

---

## 3. Environment & Local Execution Gotchas (Important for Antigravity)

1. **Python Version**:
   * **Do NOT use Python 3.14** on Windows: It requires MSVC C++ build tools (`link.exe`) to compile `pydantic-core` from source, which will fail.
   * **Use Python 3.12**: Pre-compiled binary wheels are available. Python 3.12 is located at:
     ```powershell
     & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
     ```
2. **PowerShell Script Policy**:
   * Running `.venv\Scripts\Activate.ps1` will trigger `PSSecurityException`. Always invoke Python and Pip directly:
     ```powershell
     # Install backend dependencies
     & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
     
     # Run FastAPI server
     & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
     ```
3. **Node / NPM**:
   * On Windows PowerShell, invoke `npm.cmd` and `npx.cmd` rather than bare `npm`.
   * The frontend server runs with:
     ```powershell
     cd frontend
     npm.cmd run dev
     ```

---

## 4. Dual-Mode Database Architecture

In [`backend/repositories/database.py`](file:///c:/Users/Zeal%20Shah/Google%20AI%20Builder%20Cup/Automate_Waste_Management/backend/repositories/database.py):
* If `DATABASE_BACKEND=firestore` and GCP credentials exist, it communicates with **Google Cloud Firestore**.
* If `DATABASE_BACKEND=local` (or if Firestore connection fails), it automatically falls back to an embedded **Local JSON file database** (`local_db.json`). This ensures zero-friction testing without requiring active GCP billing during local unit testing.

---

## 5. Completed Implementation Status

| Module | Status | Notes |
|---|---|---|
| **Phase 1: Architecture & Specs** | Completed | Full Markdown specs in `/docs`. |
| **Phase 2: Scaffolding & Layout** | Completed | React shell, Tailwind v4, Demo Mode badges, API CORS. |
| **Phase 3: Core Data & Ledger** | Completed | Inventory, waste, staff meals, immutable stock ledger, document schema. |
| **Phase 4: Deterministic Planning** | Completed | EOQ reorder math (`forecasting_engine.py`), buffet yields (`buffet_engine.py`), verified unit tests. |
| **Phase 5: Agentic AI Surplus** | Completed | Gemini 2.5 Flash agent (`investigation_agent.py`), tools (`tools.py`), manager approval gate (`routers/ai.py`). |
| **Phase 6: Donation Matching** | Completed | Haversine distance, cold-chain & food-type filtering, handover logging, Gemini Live Discovery toggle. |
| **Phase 7: Analytics & Dashboard**| Completed | Recharts integration, 7-day trend graph, KPI summaries. |

---

## 6. Recommended Next Steps for Your Colleague's Antigravity

1. **Live Backend API Connection**:
   * Currently, frontend views use simulated delays and realistic mocks for immediate visual feedback. Connect the frontend fetch hooks in `frontend/src/views/` to hit the live FastAPI endpoints (`http://127.0.0.1:8000/api/...`).
2. **Gemini Key Configuration**:
   * Populate `GEMINI_API_KEY` in `.env` to test real LLM responses in the Surplus Investigation panel and Gemini Live Discovery.
3. **Automated End-to-End Tests**:
   * Add Playwright or Cypress tests for the React frontend flows.
   * Expand `backend/tests/` to include mock-authenticated tenant isolation tests.
4. **Cloud Run / Firebase Deployment**:
   * Prepare `Dockerfile` for Cloud Run backend packaging and `firebase.json` for hosting frontend assets.
