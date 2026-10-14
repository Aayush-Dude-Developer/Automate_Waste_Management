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
  - Optional `limit` (1-500) returns the most recent records first; omitted means all
    records. Used by the operational screen to fetch only its latest 100 rows.
- `POST /api/waste`
  - Body: `{"date": str, "item_name": str, "quantity": float, "unit": str, "reason": str, "checked_by": str, "inventory_item_id": Optional[str]}`.
  - Automatically posts corresponding negative stock movement to inventory ledger.
- `GET /api/staff-meals`
  - Optional `limit` (1-500) returns the most recent records first; omitted means all
    records.
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
- `GET /api/purchase-recommendations?forecast_period_days=7`
  - Uses the bounded 56-day, weekday-based net-sales baseline and active recipe
    ingredient requirements to forecast raw stock demand, applying configured yield
    conversions once. Returns projected stockout/order dates, incoming ordered
    recommendations, supplier constraints, prices, source data and reliability warnings.
  - Forecast period is 1-28 days (default 7); supplier lead time is included in the
    stock projection. Ingredients without relevant sales history do not receive an
    invented demand or purchase quantity.
- `PATCH /api/purchase-recommendations/{recommendation_id}/status`
  - Body includes `status` (`approved`, `ordered`, or `received`), `ingredient_id`,
    `forecast_start_date` and `forecast_period_days`. Ordered status also requires an
    order reference and expected delivery date; received status requires a matching
    verified purchase line. Approval records the calculated quantity for subsequent
    incoming-stock projections. This endpoint never submits an order to a supplier.
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

## 6. Ingredient, Purchase, Recipe, Sale & Monthly Stock Control
- `POST /api/purchases` and `GET /api/purchases`
  - Create and list invoice headers with multiple expiry-/batch-specific ingredient lines.
  - Optional GET `limit` (1-500) returns most recent invoices first.
  - New invoices remain pending and do not change stock.
- `POST /api/purchases/{purchase_id}/verify`
  - Requires a received date; posts only received quantities in inventory input units
    and initializes their per-line remaining batch balance when lot tracking is enabled.
  - Repeated verification and duplicate supplier/invoice numbers do not add stock twice.
- `POST /api/recipes` and `GET /api/recipes`
  - Store recipe/menu versions and multiple ingredient rows, including batch servings,
    required preparation stages, units, and yield-stage references.
- `POST /api/sales` and `GET /api/sales`
  - Store sale, cancellation, net sold, prepared quantity, amount, and source.
  - Optional GET `limit` (1-500) returns most recent sales first.
  - Ingredient ledger movements use net portions unless actual prepared portions are supplied.
  - For lot-tracked inventory, negative sales, staff, waste, and manual stock movements
    decrement verified, unexpired purchase lines by earliest expiry and save allocations
    on the immutable stock movement. Expired lots are not eligible for consumption.
  - A shared optional `source_reference` prevents the same transaction being posted as
    both a sale and a staff meal.
- `POST /api/staff-consumptions` and `GET /api/staff-consumptions`
  - Record direct raw ingredient quantities or recipe portions; stock movements are
    converted to each ingredient's input unit.
  - Optional GET `limit` (1-500) returns most recent records first.
- `POST /api/stock/waste-records` and `GET /api/stock/waste-records`
  - Record raw ingredient waste or prepared-food surplus. Only raw waste posts an
    ingredient stock movement.
  - Optional GET `limit` (1-500) returns most recent records first.
- `GET /api/stock-balances/{YYYY-MM}`
  - Calculates monthly movement totals and calculated closing stock in input units.
- `POST /api/stock-balances/{YYYY-MM}/{ingredient_id}/stocktake`
  - Records the verified actual closing stock separately and returns actual minus
    calculated as the stock variance.
- `GET /api/theoretical-consumption/{YYYY-MM}`
  - Aggregates net recipe portions sold using batch serving counts and one reverse
    conversion per configured yield stage. This report is distinct from actual ledger use.

---

## 7. Agentic AI Surplus Investigation & Interventions
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

## 8. Donation Centre Discovery & Multi-Criteria Matching
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
- `GET /api/donations/handovers`
  - Optional `limit` (1-500) returns the most recent handovers first; omitted means all
    records. The impact screen previews 100 and loads all records only for CSV export.
- `POST /api/donations/records`
  - Body: `{"centre_id": str, "items": List[dict], "pickup_date": str, "contact_notes": str}`.
  - Creates donation dispatch record with status `PROPOSED`.
- `PUT /api/donations/records/{donation_id}/status`
  - Body: `{"status": str, "actual_donated_kg": Optional[float]}`.
  - Updates status to `ACCEPTED`, `HANDED_OVER`, or `DECLINED`.

---

## 9. Impact & Analytics
- `GET /api/analytics/dashboard`
  - Returns dashboard KPIs for seven-day waste, prior-week waste trend,
    inventory items at reorder risk, pending interventions, and handover count.
    Includes the seven-day waste chart points so the dashboard does not need a
    separate waste-trend request. Waste reads are limited to the prior two weeks;
    collection counts use Firestore aggregation queries.
- `GET /api/analytics/waste-trend`
  - Returns seven daily waste totals; the dashboard already receives these points
    as part of `/api/analytics/dashboard`.
