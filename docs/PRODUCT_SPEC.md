# Product Specification: Food Waste Management and Inventory Optimization (SustainBite / Taiken Ops)

## 1. Product Overview & Core Mission
The application is a comprehensive Food Waste Management and Inventory Optimization platform tailored for high-volume commercial kitchens, restaurants, and hospitality buffets (with operational ground-truth based on Taiken Pan Asian / Culinary Divergence Pvt. Ltd.).

The platform answers five foundational questions daily:
1. **What inventory do we need?** (Automated ingredient replenishment recommendations based on sales velocity, lead times, safety stocks, and pending orders)
2. **What quantity should we prepare?** (Buffet and batch meal production planning balancing shortage risk vs overproduction waste)
3. **What food is likely to become surplus or waste?** (Early-warning surplus risk detection across perishable inventory and prepared batch food)
4. **What is the best feasible action to prevent that waste?** (Agentic AI investigation proposing root-cause interventions: order adjustments, production trimming, menu specials/flash discounts, recipe yield reviews)
5. **If food is eligible for donation, which verified donation centre is the best match?** (Strict compatibility matching against verified food bank criteria: cooked vs raw, cold-chain, minimum quantities, pickup logistics, food-safety certification)

---

## 2. Real-World Document Analysis & Field Ground Truth
Based on the restaurant's operational physical sheets:
1. **Physical Wastage Record Form (Taiken)**:
   - Fields: `Date`, `Item`, `Qty`, `Unit`, `Reason`, `Checked By` (Signature).
   - Observed Units: `grm`/`gm`, `kg`, `ml`, `piece`.
   - Observed Reasons: `Broken` (noodles), `Spoiled`/`Spoil`/`Overripe` (produce), `Scrap` (trimming during prep), `By mistake` (accidental human error / recipe spillage).
   - Provenance: Must capture document image ID, row number, and require verification before committing to waste logs.
2. **Staff Meal Consumption Record Form (Taiken - Kharadi)**:
   - Fields: `Outlet`, `Date`, `Day`, `Staff on Shift` (head count, e.g., 13), `Shift` (Lunch / Dinner), `Prepared By`, `Verified By Duty Manager`.
   - Ingredients recorded: Chicken, Dal, Onion, Tomato, Chilli, Garlic, Cabbage, Carrot, Rice.
   - Crucial Rule: Staff meals consume real stock but **must never be counted as waste**. Must be deducted from stock and factored into replenishment forecasts separately from customer sales.
3. **Dry Store In Stock Register (Taiken Pan Asian - Nyati Plaza)**:
   - Fields: `Sr.No`, `Description` (including packaging size, e.g. 500gm, 1.9L), `Brand` (Lee Kum Kee, Hisashi, MBK, etc.), `In Store` (unopened pack count / kg / L), `In Use` (opened working quantity in kitchen prep line).
   - Crucial Rule: Dual-tier inventory: Store inventory (warehouse/backstore) + Kitchen-line in-use quantity.
4. **Culinary Yield & Reconciliation Notes (Operational Reality)**:
   - Yield wastage for vegetables (peeling, trimming, seeds).
   - Raw-to-cooked yield multipliers (e.g. 1 kg raw rice -> ~2.5 kg cooked rice).
   - Theoretical vs Actual consumption formula:
     $$\text{Closing Stock} = \text{Opening Stock} + \text{Received} + \text{Adjustments} - \text{Sales Consumption} - \text{Staff Meals} - \text{Recorded Waste}$$
     Any variance indicates unaccounted shrinkage or unrecorded recipe deviations.

---

## 3. Scope and Module Boundaries

### Module 1: Restaurant Setup & Authentication
- Tenant isolation by `restaurant_id`. All inventory, recipes, sales, staff logs, and donation records are strictly partitioned.
- Roles: `Manager/Owner` (approval authority, configuration, administrative directory management) and `Kitchen Staff` (data entry, physical sheet scanning, waste logging).
- Outlets: Support multi-outlet metadata (e.g. Taiken - Kharadi, Nyati Plaza) with timezone, default currency (INR ₹), and operating shifts (Lunch, Dinner, Buffet).

### Module 2: Document Scanning & Ingestion Pipeline
- Accepts: PDF, JPG, PNG, CSV, Excel.
- Hybrid ingestion: Multimodal Gemini extraction for handwritten registers + deterministic CSV/Excel parsing.
- Human-in-the-loop review: Extraction preview table highlighting uncertain values, missing units, or duplicate document hashes.

### Module 3: Central Inventory Management & Variance Reconciliation
- Real-time stock visibility across dry store, cold store, and prep line.
- Transparent status: `In Stock`, `Low Stock`, `Reorder Recommended`, `Overstock Risk`, `Near Expiry`, `Expired`, `Insufficient Data`.
- Complete audit ledger: Every transaction (Received, Recipe Usage, Staff Consumption, Waste, Audit Adjustment) is recorded immutably.

### Module 4: Sales, Purchasing & Demand Analysis
- Daily/weekly sales tracking by menu item, meal period, and category.
- Purchase order history with supplier pricing and lead-time tracking.
- Recipe mapping (BOM - Bill of Materials) linking menu items to raw ingredients with yield factors.

### Module 5: Deterministic Demand Forecasting & Restocking Engine
- Mathematical baseline: Moving averages, day-of-week seasonality, lead-time demand, and configurable safety stock buffers.
- Reorder formula:
  $$\text{Net Reorder Quantity} = \max(0, \text{Forecast Demand over Lead Time} + \text{Safety Stock} - \text{Usable Stock} - \text{Incoming Purchase Orders})$$
- Pack-size rounding and minimum order quantity (MOQ) enforcement.
- Daily Inventory Brief with clear business explanations.

### Module 6: Buffet & Prepared-Food Production Planning
- Target: Optimal batch sizing for buffets to prevent end-of-service surplus.
- Inputs: Expected guest covers, historical per-cover consumption rates, dish popularity, safety buffer percentage.
- Outputs: Recommended batch count and cooked portion targets, recipe ingredient pull lists, predicted surplus risk.

### Module 7: Agentic AI Food-Surplus Investigation
- Autonomous investigation agent that evaluates items with high surplus or waste risk.
- Tool-calling enabled: Queries sales trends, recent waste logs, upcoming reservations, and supplier deliveries.
- Produces structured diagnostic reports: root causes, facts vs hypotheses, evaluated interventions (discounting, production trimming, recipe review, donation).
- Consequential actions require explicit human manager approval.

### Module 8: Verified Donation Centre Discovery & Routing
- Curated directory of verified charities and food banks.
- Strict multi-criteria matching engine:
  - Food category compatibility (Cooked food vs Raw produce vs Dry pantry)
  - Temperature/Handling requirements (Hot holding, Chilled, Ambient)
  - Minimum and maximum quantity thresholds
  - Pickup logistics, service radius, and verified fees (no invented charges)
  - Operating hours and required notice windows
- Full donation lifecycle: Proposed -> Manager Approved -> Coordinator Contacted -> Accepted/Declined -> Handover & Verified Outcome.

### Module 9: Food Safety & Eligibility Guardrails
- Hard safety thresholds based on FSSAI / standard food safety protocols:
  - Maximum 4-hour hot-holding rule for prepared food before refrigeration or donation dispatch.
  - Prohibition of expired ingredients or temperature-abused items from donation.
  - Gemini is forbidden from certifying food as safe without deterministic checklist validation.

### Module 10: Operational Impact & Waste Reduction Dashboard
- Real-time KPIs derived directly from database records:
  - Total Waste Recorded (kg & ₹)
  - Waste Breakdown by Reason (Broken, Spoilage, Overproduction, Trimming Scrap, Mistakes)
  - Staff Meal Consumption (kg & cost)
  - Confirmed Food Saved & Donated (kg & meals served)
  - Financial Savings from Avoided Waste & Optimized Ordering
  - Audit log and recommendation approval rate.
