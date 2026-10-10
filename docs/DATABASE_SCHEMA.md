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
    ├── ai_investigations/{investigation_id}
    ├── recommendations/{recommendation_id}
    ├── donation_records/{donation_id}
    ├── documents/{document_id}
    └── audit_logs/{log_id}

/global_donation_centres/{centre_id}  (Shared verified charity directory, read-only for tenants)
```

---

## 2. Collection Schemas & Field Definitions

### 2.1 `restaurants`
- `id` (string, UUID): e.g. `"taiken_kharadi"`
- `name` (string): `"Taiken Pan Asian"`
- `outlet_name` (string): `"Kharadi Outlet"`
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
