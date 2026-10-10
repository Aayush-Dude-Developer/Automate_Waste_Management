# API Specification (FastAPI REST Endpoints)

All endpoints require the HTTP header `X-Restaurant-Id: <restaurant_id>` (defaulting to demo `"taiken_kharadi"`).

## 1. System & Authentication
- `GET /api/health`
  - Health check returning API status, active database backend (`firestore` or `local_fallback`), and Gemini model readiness.
- `GET /api/restaurant/profile`
  - Returns restaurant profile, active shifts, currency, and settings.
- `PUT /api/restaurant/profile`
  - Updates restaurant settings.

---

## 2. Inventory & Stock Ledger
- `GET /api/inventory`
  - Query params: `category`, `status`, `search`, `storage_location`.
  - Returns array of `InventoryItemResponse` with real-time stock levels, days of stock remaining, and status indicators.
- `POST /api/inventory/items`
  - Creates a new inventory item.
- `PUT /api/inventory/items/{item_id}`
  - Updates item metadata, yield factor, safety stock, or cost.
- `POST /api/inventory/adjustments`
  - Body: `{"item_id": str, "movement_type": str, "quantity_delta": float, "unit": str, "reason": str}`.
  - Commits transaction to stock ledger and recalculates on-hand balances.
- `GET /api/inventory/movements`
  - Query params: `item_id`, `limit`, `start_date`.
  - Returns immutable ledger audit history.

---

## 3. Wastage & Staff Meal Consumption (Field Forms)
- `GET /api/waste`
  - Returns list of logged waste records with reason breakdown and financial loss.
- `POST /api/waste`
  - Body: `{"date": str, "item_name": str, "quantity": float, "unit": str, "reason": str, "checked_by": str, "inventory_item_id": Optional[str]}`.
  - Automatically posts corresponding negative stock movement to inventory ledger.
- `GET /api/staff-meals`
  - Returns historical staff meal consumption records and shift counts.
- `POST /api/staff-meals`
  - Body: `{"date": str, "shift": str, "staff_count": int, "prepared_by": str, "verified_by": str, "items": [{"ingredient_name": str, "quantity": float, "unit": str}]}`.
  - Atomically creates record and deducts ingredients from store inventory.

---

## 4. Document Ingestion & Multimodal OCR
- `POST /api/documents/upload`
  - Multipart form upload (`file: UploadFile`, `document_type_hint: Optional[str]`).
  - Computes SHA-256 hash to detect duplicate uploads.
  - Calls Gemini 2.5 Flash / PDF parser to extract tabular structures.
  - Returns `ExtractionPreviewResponse` with confidence scores, ambiguous fields flagged for human review, and field mappings.
- `POST /api/documents/confirm-import`
  - Body: `{"document_id": str, "confirmed_records": List[dict], "target_entity": str}`.
  - Validates and bulk-commits approved records into target collection (`waste_records`, `staff_meal_records`, or `inventory_items`).

---

## 5. Forecasting & Buffet Planning
- `GET /api/forecasting/replenishment`
  - Returns deterministic reorder recommendations across all inventory items:
    - Lead time demand forecast
    - Safety stock target
    - Net recommended purchase quantity (rounded to pack size)
    - Suggested supplier and financial estimate
- `GET /api/buffet/plans`
  - Returns historical and scheduled buffet production plans.
- `POST /api/buffet/plans/generate`
  - Body: `{"plan_date": str, "meal_period": str, "expected_covers": int, "buffer_percent": float}`.
  - Returns calculated batch counts, cooked portion targets, and raw ingredient pull list.
- `PUT /api/buffet/plans/{plan_id}/approve`
  - Records manager sign-off on production plan.
- `POST /api/buffet/plans/{plan_id}/actuals`
  - Body: `{"dishes": [{"menu_item_id": str, "actual_leftovers": float, "actual_waste": float}]}`.
  - Records actual outcomes for forecast accuracy feedback.

---

## 6. Agentic AI Surplus Investigation & Interventions
- `POST /api/ai/investigate-surplus`
  - Body: `{"target_item_id": str, "service_date": str}`.
  - Runs Gemini Agent with function calling:
    - Queries sales trends, recent waste logs, current inventory balance, and reservations.
    - Evaluates root causes and isolates verified facts vs hypotheses.
    - Formulates prioritized interventions.
  - Returns structured `SurplusInvestigationResponse`.
- `POST /api/ai/investigations/{investigation_id}/approve-action`
  - Body: `{"selected_action_id": str, "notes": str}`.
  - Commits approved manager action to audit log and triggers downstream workflow (e.g. prepares donation voucher or adjusts PO).

---

## 7. Donation Centre Discovery & Multi-Criteria Matching
- `GET /api/donations/centres`
  - Query params: `verified_only: bool`, `accepts_cooked: bool`.
  - Returns directory of verified donation centres with pickup terms, costs, and contact info.
- `POST /api/donations/match`
  - Body: `{"food_name": str, "food_type": str, "quantity_kg": float, "temperature_class": str, "ready_by_time": str}`.
  - Deterministically evaluates candidate food banks against:
    1. Food acceptance compatibility
    2. Minimum quantity threshold
    3. Maximum radius & pickup availability
    4. Safe transit time window
  - Returns ranked list of compatible centres with transparent match rationale and unverified warnings.
- `POST /api/donations/records`
  - Body: `{"centre_id": str, "items": List[dict], "pickup_date": str, "contact_notes": str}`.
  - Creates donation dispatch record with status `PROPOSED`.
- `PUT /api/donations/records/{donation_id}/status`
  - Body: `{"status": str, "actual_donated_kg": Optional[float]}`.
  - Updates status to `ACCEPTED`, `HANDED_OVER`, or `DECLINED`.

---

## 8. Impact & Analytics
- `GET /api/analytics/dashboard`
  - Returns aggregated KPIs:
    - Waste by weight and cost (categorized by reason)
    - Food diverted and donated
    - Staff meal consumption vs total stock usage
    - Financial savings achieved
    - Daily brief summary
