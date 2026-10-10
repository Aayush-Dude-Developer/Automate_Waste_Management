# System Architecture: Food Waste Management and Inventory Optimization

## 1. High-Level Architecture Overview

The system is engineered as a decoupled, full-stack enterprise web application optimized for high reliability, strict tenant isolation, and clear separation between deterministic business computation and Generative AI reasoning.

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client (React 18 + Vite + TS + Tailwind)"]
        UI["Modern Responsive UI"]
        Dashboard["Operations Dashboard"]
        InvUI["Inventory & Movements"]
        BuffetUI["Buffet Production Planner"]
        SurplusUI["Surplus & Waste AI Console"]
        DonationUI["Donation Centre Router"]
        DocUI["Document Upload & Review"]
        ImpactUI["Impact & Savings Analytics"]
    end

    subgraph APILayer["Backend API (FastAPI / Python)"]
        Router["REST API Router (FastAPI)"]
        AuthMiddleware["Tenant Scoping & Auth Middleware"]
        DocService["Document Ingestion & OCR Service"]
        InvService["Inventory & Ledger Service"]
        ForecastEngine["Deterministic Forecasting Engine"]
        BuffetEngine["Buffet Production Calculation Engine"]
        DonationEngine["Donation Multi-Criteria Matching Engine"]
        AgentLayer["Gemini 2.5 Agent & Tool Orchestrator"]
    end

    subgraph DataLayer["Persistence & Storage"]
        Firestore["Google Cloud Firestore (or Local Adapter)"]
        Storage["Cloud Storage / Local Uploads Storage"]
    end

    subgraph ExternalAI["Google AI Services"]
        GeminiFlash["Gemini 2.5 Flash (Multimodal OCR & Agent Investigation)"]
    end

    UI --> Router
    Router --> AuthMiddleware
    AuthMiddleware --> DocService
    AuthMiddleware --> InvService
    AuthMiddleware --> ForecastEngine
    AuthMiddleware --> BuffetEngine
    AuthMiddleware --> DonationEngine
    AuthMiddleware --> AgentLayer

    DocService --> Storage
    DocService --> GeminiFlash
    AgentLayer --> GeminiFlash
    AgentLayer -.->|Tool Calls| InvService
    AgentLayer -.->|Tool Calls| ForecastEngine
    AgentLayer -.->|Tool Calls| DonationEngine

    InvService --> Firestore
    ForecastEngine --> Firestore
    BuffetEngine --> Firestore
    DonationEngine --> Firestore
    DocService --> Firestore
```

---

## 2. Component Breakdown

### 2.1 Frontend Architecture (`/frontend`)
- **Framework**: React 18, TypeScript, Vite.
- **Styling**: Tailwind CSS with custom restaurant design system (emerald/amber/slate palette for food ops).
- **Icons**: Lucide React.
- **Visualizations**: Recharts for demand trends, waste breakdown, and variance charts.
- **State & Data Fetching**: Standard React custom hooks (`useInventory`, `useForecast`, `useAgentInvestigation`, `useDonations`) with optimistic updates and robust error boundaries.
- **Key Modules**:
  1. `DashboardView`: Real-time stock alerts, today's buffet plan summary, pending waste interventions, donation matches.
  2. `InventoryView`: Searchable table with stock levels, batch/expiry alerts, manual adjustments, and historical stock movements.
  3. `DocumentUploadView`: Drag-and-drop file upload for handwritten forms, invoice PDFs, and Excel sheets with an interactive review table before database commit.
  4. `BuffetPlanningView`: Service-specific production planner with cover projections, batch sizing, and ingredient pull lists.
  5. `SurplusInvestigationView`: AI Agent workspace displaying root-cause diagnostics, evidence logs, intervention options, and manager approval buttons.
  6. `DonationDirectoryView`: Verified charity directory, criteria filters, and live matching modal with pickup fee transparency.
  7. `ImpactAnalyticsView`: Operational financial savings, food waste diverted from landfill, and forecast accuracy metrics.

### 2.2 Backend Architecture (`/backend`)
- **Framework**: FastAPI (Python 3.11+).
- **API Design**: OpenAPI / Swagger compliant REST endpoints with strict Pydantic v2 data models.
- **Architecture Pattern**: Clean Architecture with Service-Repository pattern:
  - `routers/`: HTTP transport layer, request validation, response serialization.
  - `services/`: Core business logic, stock ledger transactions, math calculations.
  - `engines/`: Pure deterministic mathematical engines (forecasting, EOQ, buffet batching, charity distance/criteria matching).
  - `agents/`: Gemini-powered agents, prompt templates, structured tool declarations.
  - `repositories/`: Database abstraction layer (Firestore client with transparent local filesystem fallback).
  - `schemas/`: Pydantic request, response, and domain models.

### 2.3 AI Agent & Tool Calling Architecture
The AI layer never performs direct unvalidated database writes or loose math. It operates in an agentic loop:

```mermaid
sequenceDiagram
    autonumber
    actor Manager as Restaurant Manager
    participant UI as Frontend App
    participant Agent as AI Investigation Agent (Gemini)
    participant Tools as Deterministic Backend Tools
    participant DB as Firestore Database

    Manager->>UI: Request surplus investigation on "Chicken Leg"
    UI->>Agent: Run investigation prompt with restaurant context
    Agent->>Tools: call `get_inventory_item(item_id)`
    Tools->>DB: Fetch current stock & batch details
    DB-->>Tools: Return 1500g in store, 200g scrap waste logged
    Tools-->>Agent: Inventory & Waste records
    Agent->>Tools: call `get_sales_and_consumption_trend(item_id, 14)`
    Tools->>DB: Fetch sales, recipes, and staff meal history
    DB-->>Tools: Lunch demand 600g, Staff meal 3000g, Declining sales
    Tools-->>Agent: Trend data & prep yield factor
    Agent->>Tools: call `check_donation_eligibility(item_id)`
    Tools-->>Agent: Raw chilled meat: Eligible if cold-chain intact
    Agent->>UI: Present Root Cause, Facts vs Hypotheses, 3 Interventions
    Manager->>UI: Approves Intervention (e.g. Schedule Donation & Trim Prep)
    UI->>Tools: Execute approved action & record audit log
    Tools->>DB: Update production buffer & create donation task
```

---

## 3. Storage and Database Strategy
- **Primary Database**: Google Cloud Firestore.
  - Document paths structured under `/restaurants/{restaurant_id}/{collection_name}/{doc_id}` to guarantee absolute tenant isolation.
- **Local Fallback Adapter**: When developing without GCP credentials or offline, the repository automatically utilizes a JSON-backed Local Firestore Repository that replicates Firestore query semantics (`where`, `order_by`, `limit`, collection-group).
- **File Storage**: Uploaded scanned forms (Taiken Wastage, Staff Meals, Stock Count) are saved in `/uploads/restaurants/{restaurant_id}/` (or Google Cloud Storage bucket in production) with cryptographic SHA-256 hash checking to prevent duplicate imports.
