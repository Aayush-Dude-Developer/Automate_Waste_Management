from backend.engines.forecasting_engine import calculate_reorder_quantity, estimate_daily_demand
from backend.engines.buffet_engine import calculate_buffet_production

def test_calculate_reorder_quantity():
    result = calculate_reorder_quantity(
        item_name="Rice",
        current_stock=10.0,
        incoming_stock=0.0,
        daily_demand_forecast=5.0,
        lead_time_days=3,
        safety_stock=5.0,
        pack_size=5.0
    )
    # Lead time demand = 15.0
    # Target stock = 20.0
    # Net requirement = 20.0 - 10.0 = 10.0
    # Pack size = 5.0 -> 2 packs -> 10.0 qty
    assert result["expected_lead_time_demand"] == 15.0
    assert result["target_stock_level"] == 20.0
    assert result["recommended_purchase_quantity"] == 10.0
    assert result["recommended_packs"] == 2.0

def test_calculate_reorder_quantity_no_order_needed():
    result = calculate_reorder_quantity(
        item_name="Chicken",
        current_stock=50.0,
        incoming_stock=10.0,
        daily_demand_forecast=5.0,
        lead_time_days=2,
        safety_stock=5.0,
        pack_size=2.0
    )
    # Target = 15.0. On hand + Incoming = 60.0.
    # Net requirement <= 0.
    assert result["recommended_purchase_quantity"] == 0.0
    assert result["recommended_packs"] == 0.0

def test_estimate_daily_demand():
    data = [10.0, 12.0, 8.0, 10.0]
    avg = estimate_daily_demand(data)
    assert avg == 10.0

def test_calculate_buffet_production():
    result = calculate_buffet_production(
        dish_name="Fried Rice",
        expected_covers=100,
        historical_consumption_per_cover=0.2, # 200g per person
        buffer_percentage=10.0,
        standard_batch_yield=5.0, # 5kg per batch
        unit="kg"
    )
    # Base requirement = 20.0 kg
    # Buffer = 2.0 kg
    # Target = 22.0 kg
    # Batches = ceil(22.0 / 5.0) = 5 batches
    # Actual production = 25.0 kg
    # Predicted surplus = 5.0 kg
    assert result["base_requirement"] == 20.0
    assert result["target_production"] == 22.0
    assert result["recommended_batches"] == 5
    assert result["actual_planned_production"] == 25.0
    assert result["predicted_surplus_portions"] == 5.0
