# AI Agent Design: Multi-Agent Architecture & Tool Calling

## 1. Core Principles
1. **Mathematical Integrity**: Gemini does NOT perform basic inventory balances, unit conversions, or arithmetic. Deterministic Python engines handle arithmetic and formulas. Gemini acts as an analytical investigator, contextual reasoning engine, and synthesis layer.
2. **Strict Tool Calling Guardrails**: The agent only reads application state through validated tool functions. The agent has no arbitrary SQL/NoSQL or file system access.
3. **Fact vs Hypothesis Separation**: The agent's schema forces it to split diagnostic conclusions into:
   - `verified_facts`: Directly proven by database records (e.g., "700g noodles broken on 19/08 and 400g on 31/08").
   - `hypotheses`: Plausible interpretations (e.g., "Prep cooks might be handling dried noodle bundles with excessive pressure during station stocking").
   - `data_gaps`: Missing records (e.g., "No supplier batch ID recorded on physical sheet to rule out brittle delivery lot").
4. **Human-in-the-Loop Consequential Actions**: Consequential actions (adjusting stock, finalizing purchase orders, committing donations) generate pending action requests that require explicit restaurant manager sign-off.

---

## 2. Agent Responsibilities

### 2.1 Agent A: Multimodal Document Ingestion & Classification Agent
- **Model**: `gemini-2.5-flash`
- **Objective**: Ingest scans/photos of physical restaurant registers (Wastage Record Form, Staff Meal Record, Dry Store Stock Sheets, Purchase Invoices).
- **Execution Flow**:
  1. Classifies document category based on visual layout and header keywords (`TAIKEN WASTAGE RECORD`, `STAFF MEAL CONSUMPTION`, `DRY STORE IN STOCK`).
  2. Extracts tabular rows with line-by-line bounding coordinates/row numbers.
  3. Maps extracted names to standard inventory SKUs (e.g. handwritten `"chinese noodles"` -> SKU `"Chinese Noodles 10mm"`).
  4. Flags ambiguous or illegible values with a confidence threshold < 0.85 (e.g., handwritten `150 gm` vs `1.5 kg` rice).
  5. Outputs strict JSON compliant with Pydantic `ExtractionPreviewSchema`.

### 2.2 Agent B: Food Surplus & Waste Investigation Agent
- **Model**: `gemini-2.5-flash`
- **Objective**: Conducts an autonomous root-cause post-mortem or pre-service risk investigation when an item exhibits high surplus or waste variance.
- **Available Backend Tools**:
  - `get_inventory_status(item_id: str)`: Returns on-hand store/line stock, cost, unit, and shelf-life.
  - `get_sales_history(item_id: str, days: int)`: Returns sales velocity and meal-period breakdown.
  - `get_waste_history(item_id: str, days: int)`: Returns historical waste reasons, quantities, and dates.
  - `get_staff_consumption_history(item_id: str, days: int)`: Returns shift consumption to prevent confusing staff food with shrinkage.
  - `get_upcoming_buffet_demand(item_id: str, date: str)`: Returns scheduled buffet requirements.
  - `check_donation_eligibility(item_id: str, temperature_class: str, hours_since_prep: float)`: Runs food safety criteria checks.
- **Agent Output Schema**:
  ```json
  {
    "investigation_summary": "Detailed diagnostic explanation",
    "verified_facts": ["string"],
    "hypotheses": ["string"],
    "data_gaps": ["string"],
    "financial_risk_inr": 1250.0,
    "recommended_interventions": [
      {
        "intervention_id": "act_01",
        "action_type": "TRIM_PRODUCTION",
        "title": "Reduce batch preparation by 25%",
        "rationale": "Historical Tuesday dinner demand averages 12 portions less than Friday/Saturday.",
        "expected_saving_inr": 850.0,
        "requires_manager_approval": true
      }
    ]
  }
  ```

### 2.3 Agent C: Donation Matching & Logistics Advisor
- **Model**: `gemini-2.5-flash`
- **Objective**: When surplus food is flagged and eligible for redistribution, this agent reviews candidate donation centres matched by the deterministic engine.
- **Backend Tools**:
  - `query_compatible_donation_centres(food_type: str, quantity_kg: float, requires_pickup: bool)`
  - `get_donation_centre_protocol(centre_id: str)`
- **Behavior**:
  - Formulates an actionable handover plan for kitchen staff: required packaging (e.g. food-grade foil containers, temperature log sheet), pickup timing window, and contact coordinator.
  - Explicitly highlights unverified details (e.g., "Notice period: 2 hours is confirmed; weekend pickup availability is unverified - call coordinator before dispatch").

---

## 3. Fallback and Resilience Strategy
- If `GEMINI_API_KEY` is absent or the Gemini API returns a rate limit or network error:
  - The application automatically switches to deterministic rule-based analysis:
    - Rule-based surplus detection: Compares available stock against 7-day average sales.
    - Rule-based donation matching: Runs standard database filter on `accepts_cooked_food` and `min_quantity_kg`.
    - Document Ingestion: CSV and Excel files continue to parse seamlessly via Python `pandas` / `openpyxl`. Scanned images display an informative notice that AI extraction requires an active Gemini API key.
- The UI never hangs or presents fake fabricated AI responses.
