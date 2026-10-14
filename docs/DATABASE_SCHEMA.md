# Database Schema Specification (Firestore)

## 1. Tenant Isolation Architecture
All operational collections are subcollections of the top-level `restaurants` collection to strictly guarantee multi-tenant data isolation:

```text
/restaurants/{restaurant_id}/
    ├── profile (Document)
    ├── inventory_items/{item_id}
    ├── stock_movements/{movement_id}
    ├── waste_records/{waste_id}
    ├── staff_meal_records/{record_id}
    ├── menu_items/{menu_item_id}
    ├── recipes/{recipe_id}
    ├── sales_records/{sale_id}
    ├── purchase_records/{purchase_id}
    ├── suppliers/{supplier_id}
    ├── buffet_plans/{plan_id}
    ├── purchase_recommendations/{recommendation_id}
    ├── ai_investigations/{investigation_id}
    ├── recommendations/{recommendation_id}
    ├── donation_records/{donation_id}
    ├── documents/{document_id}
    └── audit_logs/{log_id}

/global_donation_centres/{centre_id}  (Shared verified charity directory, read-only for tenants)
```

### 2.0 Stock control, purchasing, recipes, and sales

Operational quantity fields use each ingredient's `input_unit` (legacy alias: `base_unit`).
The document store uses stable document IDs and `ingredient_id` aliases instead of relational
DDL; references below are tenant-scoped IDs. Existing documents are retained and new fields
are additive. There is no SQL migration or database reset.

#### `inventory_items/{ingredient_id}`
- `ingredient_id` (string): same stable identifier as document `id`
- `item_name`, `yield_percentage` (signed; greater than -100), `yield_type`
  (`negative`, `positive`, `no change`), `yield_stage`
- `yield_stages` (ordered array): `stage_name`, `input_stage`, `output_stage`,
  `input_unit`, `output_unit`, `yield_percentage`; supports multiple preparation steps
- `input_unit`, `output_unit` (unit strings; `base_unit` remains supported)
- `unit_cost` (input-unit price; legacy alias `unit_cost_inr`)
- `stock_in_store`, `stock_in_use` (legacy aliases:
  `current_quantity_in_store`, `current_quantity_in_use`)
- `reorder_threshold`, `safety_stock`, `supplier_id`, `lead_time_days`
- Existing category, location, SKU, brand, shelf-life, status, tenant, and timestamp
  fields remain supported.

Yield conversion follows
`output = input * (1 + yield_percentage / 100)`. For each applicable preparation step,
convert required output quantity back by dividing by `1 + yield_percentage / 100`.
The steps are applied once in reverse order only when a recipe stage differs from raw
stock stage. Unit conversions are explicit for mass, volume, and count; incompatible or
unknown units are rejected rather than guessed.

#### `monthly_stock_balances/{ingredient_id}_{YYYY-MM}`
- `ingredient_id`, `month` (YYYY-MM), `opening_stock`
- `total_purchased_stock`, `total_recipe_consumption`, `total_staff_consumption`,
  `total_wasted_stock`, `other_stock_inflows`, `other_stock_outflows`
- `calculated_closing_stock`, `actual_closing_stock`, `stock_variance`
- `physical_count_verified`, `provisional`, verifier and verification timestamp

The calculated closing balance is opening + purchases + other inflows - recipe
consumption - staff consumption - waste - other outflows, aggregated from the stock
movement ledger. Physical counts are entered separately; variance is actual minus
calculated. A verified prior-month physical count carries forward as opening. Otherwise
the previous calculated close carries forward with a provisional flag.

#### `purchase_invoices/{purchase_id}` and `purchase_lines/{purchase_line_id}`
- Invoice: `purchase_id`, `supplier_id`, `invoice_number`, `invoice_date`,
  `received_date`, `total_amount`, `bill_document_url`, `verification_status`
- Line: `purchase_line_id`, `purchase_id`, `ingredient_id`, `quantity_purchased`,
  `purchase_unit`, `unit_price`, `quantity_received`, `expiry_date`, `batch_number`,
  `usable_quantity`, `usable_unit` (the ingredient input unit),
  `remaining_usable_quantity` (verified stock remaining in that batch)
- Each line/batch is independently recorded; unique invoice IDs derive from normalized
  supplier and invoice number. Stock is posted only after verification, in received
  quantities converted to the ingredient input unit. Deterministic ledger references
  prevent repeat verification from adding stock again.
- Inventory documents may opt into `lot_tracking_enabled`. Purchase verification
  initializes each received line's remaining balance. Sales, staff consumption, waste,
  and manual stock deductions allocate to verified, unexpired lots by earliest expiry;
  expired stock is excluded from usable stock and must be recorded as a write-off.
  Positive manual adjustments are kept separately as `untracked_stock_quantity` and
  surfaced as not expiry-adjusted. Legacy inventory without lot tracking continues to
  use its aggregate quantity and is explicitly warned about by the recommendation API.

#### `recipes/{recipe_id}` and `recipe_ingredients/{row_id}`
- Recipe: `recipe_id`, `recipe_name`, `recipe_version`, `serving_size`, `serving_unit`,
  `menu_category`, `selling_price`, `is_active`
- Ingredient row: `recipe_id`, `ingredient_id`, `required_quantity`, `required_unit`,
  `required_stage`, `yield_stage_reference`, `servings_per_batch`
- Multiple rows support multiple ingredients and reuse across recipes.

#### `purchase_recommendations/{recommendation_id}`
- Deterministic ID from forecast start date, forecast period, and ingredient ID.
- Stores approval/order/receipt state, forecast key, recommended purchase quantity,
  order reference, expected delivery date, and an optional verified purchase-line link.
- Only `ordered` records with an expected delivery date contribute incoming stock;
  verification and actual inventory posting continue to use the purchase invoice flow.
- Forecast quantities are estimates from up to 56 days of weekday-specific net recipe
  sales, bounded recent trend, recipe batch servings, and configured yields. Forecast
  records never replace actual sales, stock movements, waste, or staff consumption.

#### `daily_sales/{sale_record_id}`, `staff_consumptions/{consumption_id}`,
and `waste_records_v2/{waste_record_id}`
- Sales keep sale date, recipe, sold/cancelled/net quantities, optional actually-prepared
  quantity, net sales amount, and source. Stock movements use prepared quantity when
  provided; otherwise net sold quantity. The theoretical-consumption report always uses
  net sold portions.
- Staff consumption can be direct ingredient quantity or recipe portions; each saved
  record creates one set of raw-unit movements.
- Waste stores date, ingredient, quantity/unit, reason, stage, estimated cost, recorder,
  optional recipe, and raw-vs-prepared type. Raw waste posts a stock movement; prepared
  food surplus is informational to prevent deducting its raw ingredients twice.

These documents are available through `/api/purchases`, `/api/recipes`, `/api/sales`,
`/api/staff-consumptions`, `/api/stock/waste-records`, `/api/stock-balances/{YYYY-MM}`,
and `/api/theoretical-consumption/{YYYY-MM}`. No live Firestore data is changed by adding
these schemas and endpoints.

### Synthetic purchase recommendation demo dataset

`backend/seed_purchase_demo.py` creates a deterministic, isolated example for
`taiken_kharadi`: six `demo_` ingredients with explicit supplier lead times/MOQs/pack
sizes and yields, verified dated batch invoices, three recipes, and 56 days of net
weekday-varied sales. Records are marked `synthetic_demo=true`; do not use them for
operational purchasing, accounting, or food safety decisions. The demo includes one
expired tomato lot to demonstrate the exclusion and write-off warning. It only writes
the `demo_` record IDs and a seed metadata marker; it does not overwrite existing
operational IDs. Re-running on the same history-through date performs no writes.

From the repository root, preview the number of documents without writing:

```powershell
.\backend\.venv_312\Scripts\python.exe -m backend.seed_purchase_demo --restaurant-id taiken_kharadi
```

To write the synthetic records, set `DATABASE_BACKEND=firestore` and
`GOOGLE_CLOUD_PROJECT` in the environment, then explicitly run:

```powershell
.\backend\.venv_312\Scripts\python.exe -m backend.seed_purchase_demo --restaurant-id taiken_kharadi --apply
```

The demo batch balances sum to each demo inventory item's recorded total on hand;
the recommendations count only non-expired batch balances plus separately identified
untracked stock. This additive Firestore document model requires no SQL migration.

For existing inventory documents, preview the additive alias/default migration from the
repository root with:

```powershell
.\backend\.venv_312\Scripts\python.exe -m backend.migrations.migrate_stock_schema --restaurant-id taiken_kharadi
```

The migration assigns **illustrative**, not measured, yields to the built-in sample
ingredients (for example rice +100% at cooked, chicken -15% at trimmed); items without a
sample mapping default to 0% / no change. Review the preview and adjust actual kitchen
yields before relying on those values for purchasing or theoretical-consumption decisions.
The migration preserves inventory balances, other profile fields, and the existing
currency, and records `restaurant_yield_sg_v1`. Add `--restaurant-profile` to preview and
apply the requested India restaurant name and location. To persist after reviewing
the output, add `--apply`. Back up the Firestore project before applying changes.

### Firestore operation usage

Dashboard requests read only the recent two-week waste window and use Firestore count
aggregations for inventory risk, pending investigations, and handovers. The seven-day
chart is included in the dashboard response, avoiding a second request. Recipe and
purchase-line lookups, sales-source checks, and monthly movements are filtered in
Firestore rather than downloading whole unrelated collections. Monthly balance reads
calculate results without writing them; only a physical stocktake persists a balance.
The frontend coalesces concurrent GETs and caches successful GET results in memory for
30 seconds, clearing that cache when any mutation is sent.
Operational waste, staff-consumption, purchase, and sales screens request only the most
recent 100 records using server-side ordered limits. Their list endpoints retain the
unlimited default for compatibility; the impact-report screen previews 100 records and
loads full history only when the user explicitly exports the report.

Stock ledger and inventory writes remain separate durable documents because the ledger
is the audit trail and inventory is the current balance. This code can reduce operations,
but it cannot guarantee staying within Firebase's daily free quota: actual usage depends
on traffic, dataset size, other Firebase products, and deployed clients. Monitor Firestore
usage and billing in the Google Cloud/Firebase console.

---

## 2. Collection Schemas & Field Definitions

### 2.1 `restaurants`
- `id` (string, UUID): e.g. `"taiken_kharadi"`
- `name` (string): `"Straits Garden Kitchen"`
- `outlet_name` (string): `"Kharadi"`
- `location` / `address` (string): `"Kharadi, Pune, India"`
- `company_name` (string): `"Culinary Divergence Pvt. Ltd."`
- `cuisine_type` (string): `"Pan-Asian / Japanese / Thai / Chinese"`
- `timezone` (string): `"Asia/Kolkata"`
- `currency` (string): `"INR"` (₹)
- `operating_shifts` (array of objects): `[{"shift": "Lunch", "start": "12:00", "end": "16:00"}, {"shift": "Dinner", "start": "19:00", "end": "23:30"}]`
- `created_at` (ISO timestamp)

### 2.2 `inventory_items`
- `id` (string): e.g. `"inv_chicken_leg"`
- `restaurant_id` (string)
- `item_name` (string): `"Chicken Leg"`
- `sku` (string, optional): `"CHK-LEG-01"`
- `category` (enum): `Produce`, `Meat & Poultry`, `Seafood`, `Dry Pantry / Grocery`, `Dairy`, `Sauces & Condiments`, `Beverages`
- `brand` (string, optional): e.g. `"Lee Kum Kee"`, `"Hisashi"`, `"Chakoh"`
- `storage_location` (enum): `Dry Store`, `Cold Store / Chiller`, `Deep Freezer`, `Kitchen Line / Prep Station`
- `current_quantity_in_store` (float): Unopened warehouse stock
- `current_quantity_in_use` (float): Open active kitchen stock
- `total_current_quantity` (float): `in_store + in_use`
- `base_unit` (enum): `kg`, `gm`, `ml`, `ltr`, `piece`, `packet`
- `unit_cost_inr` (float): Cost per base unit (e.g. ₹280.00 / kg)
- `reorder_threshold` (float): Calculated or minimum safety stock level
- `safety_stock` (float): Buffer quantity
- `supplier_id` (string, optional)
- `shelf_life_days` (integer)
- `expiry_date` (ISO date, optional)
- `yield_factor` (float): Standard prep yield (e.g. 0.85 for trimmed meat, 2.50 for raw-to-cooked rice)
- `status` (enum): `in_stock`, `low_stock`, `reorder_recommended`, `overstock_risk`, `near_expiry`, `expired`
- `updated_at` (ISO timestamp)

### 2.3 `stock_movements` (Immutable Ledger)
- `id` (string, UUID)
- `restaurant_id` (string)
- `item_id` (string)
- `timestamp` (ISO timestamp)
- `movement_type` (enum): `RECEIPT_PURCHASE`, `USAGE_SALES_RECIPE`, `USAGE_STAFF_MEAL`, `WASTE_RECORDED`, `ADJUSTMENT_AUDIT`
- `quantity_delta` (float): Positive for receipts/positive audits, negative for usage/waste
- `unit` (string)
- `balance_after` (float): Snapshot of total stock after transaction
- `reference_id` (string, optional): Links to `waste_id`, `staff_record_id`, `purchase_id`, or `audit_id`
- `notes` (string)
- `created_by` (string)

### 2.4 `waste_records` (Matches Physical Taiken Wastage Form)
- `id` (string, UUID)
- `restaurant_id` (string)
- `date` (ISO date): e.g. `"2026-08-02"`
- `item_name` (string): e.g. `"Chinese Noodles"`, `"Banana Yellow"`, `"Chicken Leg"`
- `inventory_item_id` (string, nullable)
- `quantity` (float): e.g. `400`
- `unit` (string): e.g. `"gm"`, `"kg"`, `"piece"`, `"ml"`
- `reason` (enum): `BROKEN`, `SPOILED`, `SCRAP_PREPARATION`, `OVERRIPE`, `BY_MISTAKE`, `UNSOLD_OVERPRODUCTION`, `OTHER`
- `checked_by` (string): Chef or supervisor signature/name (e.g. `"Ritesh"`, `"Alicia Ho"`)
- `financial_loss_inr` (float): `quantity * unit_cost`
- `source_document_id` (string, optional): ID of scanned sheet
- `status` (enum): `VERIFIED`, `FLAGGED_REVIEW`
- `created_at` (ISO timestamp)

### 2.5 `staff_meal_records` (Matches Taiken Staff Meal Register)
- `id` (string, UUID)
- `restaurant_id` (string)
- `date` (ISO date): e.g. `"2026-09-29"`
- `shift` (enum): `LUNCH`, `DINNER`
- `staff_on_shift_count` (integer): e.g. `13`
- `prepared_by` (string): e.g. `"Ritesh"`, `"Shovit"`
- `verified_by_duty_manager` (string): e.g. `"Alicia Ho"`
- `items` (array of objects):
  - `ingredient_name` (string): e.g. `"Chicken"`, `"Dal"`, `"Rice"`
  - `inventory_item_id` (string)
  - `quantity` (float)
  - `unit` (string)
  - `remarks` (string)
- `total_cost_inr` (float)
- `deducted_from_inventory` (boolean): Default `true` upon manager approval
- `source_document_id` (string, optional)
- `created_at` (ISO timestamp)

### 2.6 `buffet_plans`
- `id` (string, UUID)
- `restaurant_id` (string)
- `plan_date` (ISO date)
- `meal_period` (enum): `LUNCH`, `DINNER`, `SUNDAY_BRUNCH`
- `expected_covers` (integer): e.g. `120`
- `service_buffer_percentage` (float): Configurable (e.g. 8.0%)
- `dishes` (array of objects):
  - `menu_item_id` (string)
  - `dish_name` (string)
  - `historical_consumption_per_cover` (float)
  - `target_cooked_portions` (float)
  - `recommended_batches` (integer)
  - `predicted_surplus_portions` (float)
  - `status` (enum): `DRAFT`, `APPROVED`, `IN_SERVICE`, `COMPLETED`
  - `actual_leftover_portions` (float, nullable)
  - `actual_waste_portions` (float, nullable)
- `manager_approved_by` (string, nullable)
- `created_at` (ISO timestamp)

### 2.7 `donation_centres` (Verified Directory)
- `id` (string): e.g. `"centre_robin_hood_army_pune"`
- `name` (string): `"Robin Hood Army - Pune Chapter"`
- `address` (string): `"Kalyani Nagar / Kharadi, Pune, Maharashtra"`
- `coordinates` (geo point): `{"lat": 18.552, "lng": 73.935}`
- `contact_person` (string): `"Amitabh K. (Logistics Lead)"`
- `contact_phone` (string): `"+91-98XXXXXXXX"`
- `contact_email` (string): `"pune@robinhoodarmy.com"`
- `food_types_accepted` (array): `["COOKED_MEALS", "FRESH_PRODUCE", "PACKAGED_DRY_GOODS"]`
- `accepts_cooked_food` (boolean): `true`
- `accepts_raw_ingredients` (boolean): `true`
- `min_quantity_kg` (float): `5.0`
- `max_quantity_kg` (float): `200.0`
- `pickup_available` (boolean): `true`
- `pickup_cost_inr` (float): `0.0` (Volunteer run - free pickup)
- `pickup_service_radius_km` (float): `12.0`
- `operating_hours` (string): `"10:00 - 22:00"`
- `required_notice_hours` (float): `2.0`
- `food_safety_packaging_rules` (array of strings): `["Insulated hot containers or foil trays", "Food prepared within 4 hours", "No raw/cooked cross-contamination"]`
- `verification_status` (enum): `VERIFIED`, `UNVERIFIED_DEMO`, `REQUIRES_REVERIFICATION`
- `last_verified_date` (ISO date): `"2026-09-15"`
- `source_of_information` (string): `"Direct NGO Partnership Registry"`

### 2.8 `ai_investigations` & `recommendations`
- `id` (string, UUID)
- `restaurant_id` (string)
- `target_item_id` (string)
- `target_item_name` (string)
- `investigation_type` (enum): `SURPLUS_RISK`, `UNUSUAL_WASTE_SPIKE`, `STOCKOUT_RISK`, `STAFF_MEAL_VARIANCE`
- `detected_metric` (object): e.g. `{"surplus_qty": 18, "unit": "portions", "at_risk_date": "2026-10-10"}`
- `root_causes` (array of strings): Synthesized by Gemini with evidence references
- `facts_vs_hypotheses` (object):
  - `verified_facts` (array of strings)
  - `hypotheses` (array of strings)
  - `data_gaps` (array of strings)
- `proposed_interventions` (array of objects):
  - `intervention_id` (string)
  - `action_type` (enum): `TRIM_PRODUCTION`, `REDUCE_PURCHASE_ORDER`, `PROMOTIONAL_DISCOUNT`, `DONATION_DISPATCH`, `RECIPE_AUDIT`
  - `title` (string)
  - `details` (string)
  - `expected_impact_inr` (float)
  - `feasibility_rating` (string): `High` / `Medium` / `Low`
- `selected_action` (string, nullable)
- `approval_status` (enum): `PENDING_MANAGER_APPROVAL`, `APPROVED`, `REJECTED`, `OVERRIDDEN`
- `approved_by` (string, nullable)
- `actual_outcome` (object, nullable): Recorded post-service (e.g. `{"actual_waste_diverted_kg": 7.2, "actual_savings_inr": 1440}`)
- `created_at` (ISO timestamp)
