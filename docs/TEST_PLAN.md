# Comprehensive Test Plan & Evaluation Methodology

## 1. Testing Philosophy
The test strategy enforces that all mathematical inventory balances, reorder calculations, buffet batching, and donation eligibility filtering are verified with automated unit and integration tests. GenAI tool calls and extraction schemas are validated against strict Pydantic schemas.

---

## 2. Test Suites

### 2.1 Unit Tests: Deterministic Calculations (`tests/test_calculations.py`)
1. **Inventory Reconciliation Formula**:
   - Verify: $\text{Closing} = \text{Opening} + \text{Received} + \text{Adjustments} - \text{Sales Consumption} - \text{Staff Meals} - \text{Waste}$.
   - Edge case: Zero stock and negative adjustment prevention.
2. **Reorder Quantity Calculation**:
   - Verify: $\text{Net} = \max(0, \text{Lead Time Demand} + \text{Safety Stock} - \text{On-Hand} - \text{PO})$.
   - Edge case: High on-hand stock results in 0 reorder quantity, not negative values.
   - Pack size rounding: e.g. item with pack size of 2kg rounding up properly.
3. **Buffet Production Batching**:
   - Inputs: Covers, per-cover historical portion, safety buffer (e.g. 10%).
   - Batch rounding: Minimum batch constraint test.
4. **Donation Matching Filter**:
   - Filter out centres where `accepts_cooked_food == False` when offering cooked buffet leftovers.
   - Filter out centres whose `min_quantity_kg` exceeds offered quantity.
   - Ensure unverified pickup costs are surfaced as "Not Confirmed" rather than 0.

### 2.2 Integration Tests: API Workflows (`tests/test_api_workflows.py`)
1. **Waste Logging Workflow**:
   - Create waste entry via `POST /api/waste`.
   - Verify stock movement created in ledger.
   - Verify on-hand stock reduced by exact quantity.
2. **Staff Meal Logging Workflow**:
   - Create staff meal record with 13 staff on shift.
   - Verify ingredients deducted from stock ledger.
   - Verify staff food is NOT counted as waste in analytics endpoint.
3. **Document Ingestion Workflow**:
   - Submit sample digital register.
   - Receive extraction preview with confidence score.
   - Commit confirmed import.
   - Verify target entities created in Firestore/Local DB.
4. **Human Approval on AI Recommendations**:
   - Trigger surplus investigation.
   - Attempt to execute consequential action without approval -> expect rejection/pending status.
   - Manager approves action -> expect state transition to APPROVED and audit trail logged.

### 2.3 Evaluation Dataset & Ground Truth
We include ground-truth test data derived directly from the user's provided Taiken restaurant forms:
- `data/samples/taiken_wastage_august.csv` (reflecting the exact entries from Taiken Wastage Record Form: Chinese noodles broken, banana spoiled, chicken scrap, sushi rice mistake).
- `data/samples/taiken_staff_meals_sept29.csv` (reflecting 29/09/2026 Kharadi staff meal record with 13 staff).
- `data/samples/taiken_dry_store_august.csv` (reflecting Taiken Pan Asian Dry Store In Stock register).
- `data/samples/verified_donation_centres.json` (Pune & Mumbai verified NGO directory).
