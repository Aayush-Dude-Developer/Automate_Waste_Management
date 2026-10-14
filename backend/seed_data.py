"""Seed clearly labeled synthetic sample data for SustainBite."""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta, timezone

# Add backend to path so we can leverage the repository layer and configs
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

from backend.config import settings
from backend.repositories.database import db

RESTAURANT_ID = settings.DEFAULT_RESTAURANT_ID

# 1. Base Inventory Definitions
INVENTORY_SEED = [
    {"id": "inv_chicken_leg", "item_name": "Chicken Leg", "category": "Meat & Poultry", "brand": "Fresh Farms", "storage_location": "Deep Freezer", "unit_cost_inr": 280.0, "base_unit": "kg", "total_current_quantity": 45.0, "reorder_threshold": 20.0, "safety_stock": 10.0, "shelf_life_days": 14, "yield_percentage": -15.0, "yield_stage": "trimmed"},
    {"id": "inv_chinese_noodles", "item_name": "Chinese Noodles", "category": "Dry Pantry / Grocery", "brand": "Ching's Secret", "storage_location": "Dry Store", "unit_cost_inr": 95.0, "base_unit": "kg", "total_current_quantity": 60.0, "reorder_threshold": 15.0, "safety_stock": 8.0, "shelf_life_days": 180, "yield_percentage": 150.0, "yield_stage": "cooked"},
    {"id": "inv_jasmine_rice", "item_name": "Jasmine Rice", "category": "Dry Pantry / Grocery", "brand": "Royal Umami", "storage_location": "Dry Store", "unit_cost_inr": 160.0, "base_unit": "kg", "total_current_quantity": 80.0, "reorder_threshold": 25.0, "safety_stock": 12.0, "shelf_life_days": 365, "yield_percentage": 100.0, "yield_stage": "cooked"},
    {"id": "inv_pak_choi", "item_name": "Pak Choi", "category": "Produce", "brand": "Hydroponic Greens", "storage_location": "Cold Store / Chiller", "unit_cost_inr": 120.0, "base_unit": "kg", "total_current_quantity": 12.5, "reorder_threshold": 8.0, "safety_stock": 4.0, "shelf_life_days": 5, "yield_percentage": -10.0, "yield_stage": "trimmed"},
    {"id": "inv_dark_soy_sauce", "item_name": "Dark Soy Sauce", "category": "Sauces & Condiments", "brand": "Lee Kum Kee", "storage_location": "Dry Store", "unit_cost_inr": 350.0, "base_unit": "ltr", "total_current_quantity": 18.0, "reorder_threshold": 6.0, "safety_stock": 3.0, "shelf_life_days": 720, "yield_percentage": 0.0, "yield_stage": "no change"},
    {"id": "inv_tofu_firm", "item_name": "Firm Tofu", "category": "Produce", "brand": "Mori-Nu", "storage_location": "Cold Store / Chiller", "unit_cost_inr": 180.0, "base_unit": "kg", "total_current_quantity": 15.0, "reorder_threshold": 8.0, "safety_stock": 4.0, "shelf_life_days": 21, "yield_percentage": -5.0, "yield_stage": "drained"},
    {"id": "inv_tiger_prawns", "item_name": "Tiger Prawns", "category": "Seafood", "brand": "Ocean Catch", "storage_location": "Deep Freezer", "unit_cost_inr": 650.0, "base_unit": "kg", "total_current_quantity": 22.0, "reorder_threshold": 10.0, "safety_stock": 5.0, "shelf_life_days": 30, "yield_percentage": -35.0, "yield_stage": "peeled"},
    {"id": "inv_coconut_milk", "item_name": "Coconut Milk", "category": "Dry Pantry / Grocery", "brand": "Chaokoh", "storage_location": "Dry Store", "unit_cost_inr": 210.0, "base_unit": "ltr", "total_current_quantity": 30.0, "reorder_threshold": 12.0, "safety_stock": 6.0, "shelf_life_days": 365, "yield_percentage": 0.0, "yield_stage": "no change"},
    {"id": "inv_thai_green_paste", "item_name": "Thai Green Curry Paste", "category": "Sauces & Condiments", "brand": "Mae Ploy", "storage_location": "Cold Store / Chiller", "unit_cost_inr": 420.0, "base_unit": "kg", "total_current_quantity": 8.0, "reorder_threshold": 4.0, "safety_stock": 2.0, "shelf_life_days": 180, "yield_percentage": 0.0, "yield_stage": "no change"},
    {"id": "inv_cooking_oil", "item_name": "Refined Sunflower Oil", "category": "Dry Pantry / Grocery", "brand": "Fortune", "storage_location": "Dry Store", "unit_cost_inr": 140.0, "base_unit": "ltr", "total_current_quantity": 90.0, "reorder_threshold": 30.0, "safety_stock": 15.0, "shelf_life_days": 365, "yield_percentage": 0.0, "yield_stage": "no change"},
    {"id": "inv_eggs", "item_name": "Farm Fresh Eggs", "category": "Dairy", "brand": "Eggoz", "storage_location": "Cold Store / Chiller", "unit_cost_inr": 7.5, "base_unit": "piece", "total_current_quantity": 250.0, "reorder_threshold": 80.0, "safety_stock": 40.0, "shelf_life_days": 25, "yield_percentage": 0.0, "yield_stage": "no change"},
    {"id": "inv_banana_yellow", "item_name": "Banana Yellow", "category": "Produce", "brand": "Local Mandi", "storage_location": "Kitchen Line / Prep Station", "unit_cost_inr": 50.0, "base_unit": "kg", "total_current_quantity": 10.0, "reorder_threshold": 5.0, "safety_stock": 2.0, "shelf_life_days": 4, "yield_percentage": -35.0, "yield_stage": "peeled"}
]

GLOBAL_CHARITIES = [
    {
        "id": "charity_robin_hood_army",
        "name": "Robin Hood Army - Pune Chapter",
        "category": "Volunteer Food Rescue",
        "contact_person": "Karan V.",
        "phone": "+91 98230 11223",
        "service_areas": ["Kharadi", "Viman Nagar", "Kalyani Nagar"],
        "accepts_cooked_food": True,
        "requires_cold_chain": False,
        "operating_hours": "18:00 - 23:30",
        "verified": False,
        "synthetic_sample_data": True,
    },
    {
        "id": "charity_feeding_india",
        "name": "Feeding India (Zomato Giving)",
        "category": "Registered NGO",
        "contact_person": "Rhea Sen",
        "phone": "+91 98765 43210",
        "service_areas": ["Pune East", "Kharadi", "Hadapsar"],
        "accepts_cooked_food": True,
        "requires_cold_chain": True,
        "operating_hours": "11:00 - 22:00",
        "verified": False,
        "synthetic_sample_data": True,
    },
    {
        "id": "charity_savitribai_orphanage",
        "name": "Savitribai Phule Children Shelter",
        "category": "Orphanage / Shelter",
        "contact_person": "Sunita Jadhav",
        "phone": "+91 94220 98765",
        "service_areas": ["Kharadi Bypass", "Wagholi"],
        "accepts_cooked_food": True,
        "requires_cold_chain": False,
        "operating_hours": "08:00 - 20:00",
        "verified": False,
        "synthetic_sample_data": True,
    }
]

def seed_database():
    now = datetime.now(timezone.utc)
    print(f"Starting seed process for restaurant: {RESTAURANT_ID}")
    print(f"Target Database Backend: {settings.DATABASE_BACKEND}")

    # 1. Global Charities
    print("-> Seeding global donation centres...")
    for charity in GLOBAL_CHARITIES:
        db.add_document("global_donation_centres", charity["id"], charity)

    # 2. Restaurant Profile
    restaurant_profile = {
        "id": RESTAURANT_ID,
        "name": "Straits Garden Kitchen",
        "outlet_name": "Kharadi",
        "location": "Kharadi, Pune, India",
        "address": "Kharadi, Pune, India",
        "cuisine_type": "Pan-Asian / Japanese / Thai / Chinese",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "synthetic_sample_data": True,
        "operating_shifts": [
            {"shift": "Lunch", "start": "12:00", "end": "16:00"},
            {"shift": "Dinner", "start": "19:00", "end": "23:30"}
        ],
        "created_at": (now - timedelta(days=370)).isoformat()
    }
    db.add_document(f"restaurants/{RESTAURANT_ID}/profile", "main", restaurant_profile)

    # 3. Inventory Items
    print("-> Seeding inventory items...")
    for item in INVENTORY_SEED:
        doc = {
            **item,
            "restaurant_id": RESTAURANT_ID,
            "ingredient_id": item["id"],
            "input_unit": item["base_unit"],
            "output_unit": item["base_unit"],
            "unit_cost": item["unit_cost_inr"],
            "stock_in_store": round(item["total_current_quantity"] * 0.7, 2),
            "stock_in_use": round(item["total_current_quantity"] * 0.3, 2),
            "current_quantity_in_store": round(item["total_current_quantity"] * 0.7, 2),
            "current_quantity_in_use": round(item["total_current_quantity"] * 0.3, 2),
            "status": "in_stock",
            "synthetic_sample_data": True,
            "yield_factor": 0.85 if item["category"] in ["Meat & Poultry", "Seafood"] else 1.0,
            "yield_type": (
                "negative" if item["yield_percentage"] < 0 else
                "positive" if item["yield_percentage"] > 0 else
                "no change"
            ),
            "yield_stages": [] if item["yield_percentage"] == 0 else [{
                "stage_name": item["yield_stage"],
                "input_stage": "raw",
                "output_stage": item["yield_stage"],
                "input_unit": item["base_unit"],
                "output_unit": item["base_unit"],
                "yield_percentage": item["yield_percentage"],
            }],
            "updated_at": now.isoformat()
        }
        db.add_document(f"restaurants/{RESTAURANT_ID}/inventory_items", item["id"], doc)

    # 4. Generate 365 Days of Historic Data
    print("-> Generating 365 days of historical logs (waste, staff meals, donations, buffet plans)...")
    
    WASTE_REASONS = ["BROKEN", "SPOILED", "SCRAP_PREPARATION", "OVERRIPE", "UNSOLD_OVERPRODUCTION"]
    CHEFS = ["Ritesh", "Shovit", "Sanjay", "Alicia Ho"]
    
    total_waste_records = 0
    total_staff_meal_records = 0
    total_donation_records = 0
    total_buffet_plans = 0

    # Iterating week by week / periodic events across past 365 days
    for day_offset in range(365, 0, -1):
        record_date = (now - timedelta(days=day_offset)).date().isoformat()
        current_dt = (now - timedelta(days=day_offset))
        day_of_week = current_dt.weekday() # 0 = Monday, 6 = Sunday

        # A. Waste records: ~2-4 waste entries per week
        if random.random() < 0.45:
            inv = random.choice(INVENTORY_SEED)
            reason = random.choice(WASTE_REASONS)
            qty = round(random.uniform(0.5, 4.0), 2)
            loss_inr = round(qty * inv["unit_cost_inr"], 2)
            
            waste_id = f"waste_{day_offset}_{str(uuid.uuid4())[:8]}"
            waste_doc = {
                "id": waste_id,
                "restaurant_id": RESTAURANT_ID,
                "date": record_date,
                "item_name": inv["item_name"],
                "inventory_item_id": inv["id"],
                "quantity": qty,
                "unit": inv["base_unit"],
                "reason": reason,
                "checked_by": random.choice(CHEFS),
                "financial_loss_inr": loss_inr,
                "status": "VERIFIED",
                "synthetic_sample_data": True,
                "created_at": current_dt.isoformat()
            }
            db.add_document(f"restaurants/{RESTAURANT_ID}/waste_records", waste_id, waste_doc)
            total_waste_records += 1

        # B. Staff meals: Logged 3-4 days a week for Lunch/Dinner
        if day_of_week in [0, 2, 4, 6]:
            meal_id = f"sm_{day_offset}_{str(uuid.uuid4())[:8]}"
            staff_count = random.randint(11, 16)
            rice_qty = round(staff_count * 0.18, 2) # ~180g per head
            chicken_or_veg_qty = round(staff_count * 0.20, 2)
            
            staff_doc = {
                "id": meal_id,
                "restaurant_id": RESTAURANT_ID,
                "date": record_date,
                "shift": "LUNCH" if random.random() < 0.5 else "DINNER",
                "staff_on_shift_count": staff_count,
                "prepared_by": random.choice(CHEFS[:2]),
                "verified_by_duty_manager": "Alicia Ho",
                "items": [
                    {"ingredient_name": "Jasmine Rice", "inventory_item_id": "inv_jasmine_rice", "quantity": rice_qty, "unit": "kg", "remarks": "Standard staff meal rice"},
                    {"ingredient_name": "Chicken Leg", "inventory_item_id": "inv_chicken_leg", "quantity": chicken_or_veg_qty, "unit": "kg", "remarks": "Curry preparation"}
                ],
                "total_cost_inr": round((rice_qty * 160.0) + (chicken_or_veg_qty * 280.0), 2),
                "deducted_from_inventory": True,
                "synthetic_sample_data": True,
                "created_at": current_dt.isoformat()
            }
            db.add_document(f"restaurants/{RESTAURANT_ID}/staff_meal_records", meal_id, staff_doc)
            total_staff_meal_records += 1

        # C. Buffet Plans: Every Friday dinner, Saturday dinner, and Sunday brunch
        if day_of_week in [4, 5, 6]:
            plan_id = f"buffet_{day_offset}_{str(uuid.uuid4())[:8]}"
            covers = random.randint(90, 160)
            buffet_doc = {
                "id": plan_id,
                "restaurant_id": RESTAURANT_ID,
                "plan_date": record_date,
                "meal_period": "SUNDAY_BRUNCH" if day_of_week == 6 else "DINNER",
                "expected_covers": covers,
                "service_buffer_percentage": 10.0,
                "dishes": [
                    {"dish_name": "Pan Asian Fried Rice", "base_demand": round(covers * 0.15, 2), "cook_batches": 3, "total_prep": round(covers * 0.165, 2)},
                    {"dish_name": "Thai Green Curry", "base_demand": round(covers * 0.18, 2), "cook_batches": 3, "total_prep": round(covers * 0.198, 2)},
                    {"dish_name": "Wok Tossed Noodles", "base_demand": round(covers * 0.14, 2), "cook_batches": 2, "total_prep": round(covers * 0.154, 2)}
                ],
                    "synthetic_sample_data": True,
                    "created_at": current_dt.isoformat()
            }
            db.add_document(f"restaurants/{RESTAURANT_ID}/buffet_plans", plan_id, buffet_doc)
            total_buffet_plans += 1

        # D. Surplus Food Donations: ~1-2 times every fortnight (Sunday nights after heavy buffets)
        if day_of_week == 6 and (day_offset % 14 == 0):
            donation_id = f"don_{day_offset}_{str(uuid.uuid4())[:8]}"
            charity = random.choice(GLOBAL_CHARITIES)
            donated_qty = round(random.uniform(5.0, 18.0), 1)
            
            don_doc = {
                "id": donation_id,
                "restaurant_id": RESTAURANT_ID,
                "date": record_date,
                "centre_id": charity["id"],
                "centre_name": charity["name"],
                "item_name": "Surplus Buffet Rice & Noodles",
                "quantity_kg": donated_qty,
                "meals_equivalent": int(donated_qty * 3.5),
                "driver_name": "Ramesh Kumar (Volunteer)",
                "food_temperature_celsius": 68.5,
                "handover_status": "COMPLETED",
                "synthetic_sample_data": True,
                "created_at": current_dt.isoformat()
            }
            db.add_document(f"restaurants/{RESTAURANT_ID}/donation_records", donation_id, don_doc)
            total_donation_records += 1

    print("\n[SUCCESS] Seed process completed successfully!")
    print(f"Summary of Records Created for [{RESTAURANT_ID}]:")
    print(f" - Inventory Items:       {len(INVENTORY_SEED)}")
    print(f" - Global Charities:      {len(GLOBAL_CHARITIES)}")
    print(f" - Waste Records:         {total_waste_records}")
    print(f" - Staff Meal Logs:       {total_staff_meal_records}")
    print(f" - Buffet Plans:          {total_buffet_plans}")
    print(f" - Food Donation Records: {total_donation_records}")

if __name__ == "__main__":
    seed_database()
