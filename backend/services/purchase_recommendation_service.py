import hashlib
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..repositories.database import db
from ..schemas.purchase_recommendations import (
    PurchaseRecommendation,
    PurchaseRecommendationDashboard,
    RecommendationDemandBasis,
    RecommendationExpiryBatch,
    RecommendationIncomingOrder,
    RecommendationStatusUpdate,
)
from .stock_service import convert_quantity, raw_ingredient_quantity


HISTORY_DAYS = 56
RECENT_TREND_DAYS = 28
MAX_TREND_FACTOR = 1.2
MIN_TREND_FACTOR = 0.8


def _path(restaurant_id: str, collection: str) -> str:
    return f"restaurants/{restaurant_id}/{collection}"


def _recommendation_id(forecast_start: date, period_days: int, ingredient_id: str) -> str:
    signature = f"{forecast_start.isoformat()}:{period_days}:{ingredient_id}"
    return "pr_" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:24]


def _date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _item_stock(item: dict[str, Any]) -> float:
    if item.get("total_current_quantity") is not None:
        return max(0.0, float(item["total_current_quantity"]))
    return max(
        0.0,
        float(item.get("current_quantity_in_store", item.get("stock_in_store", 0)))
        + float(item.get("current_quantity_in_use", item.get("stock_in_use", 0))),
    )


def _forecast_sales_by_recipe(
    sales: list[dict[str, Any]],
    recipes: dict[str, dict[str, Any]],
    forecast_days: list[date],
    history_start: date,
    history_end: date,
) -> tuple[dict[str, dict[date, float]], int, dict[str, float]]:
    daily_sales: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    distinct_sales_days: set[date] = set()
    for sale in sales:
        sale_day = _date(sale.get("sale_date"))
        recipe_id = str(sale.get("recipe_id", ""))
        if sale_day is None or recipe_id not in recipes:
            continue
        portions = max(0.0, float(sale.get("net_quantity_sold", 0) or 0))
        daily_sales[recipe_id][sale_day] += portions
        if portions > 0:
            distinct_sales_days.add(sale_day)

    history_dates = [
        history_start + timedelta(days=offset)
        for offset in range((history_end - history_start).days + 1)
    ]
    forecasts: dict[str, dict[date, float]] = {}
    trend_factors: dict[str, float] = {}
    for recipe_id in recipes:
        by_weekday: dict[int, list[float]] = defaultdict(list)
        for history_day in history_dates:
            by_weekday[history_day.weekday()].append(
                daily_sales[recipe_id].get(history_day, 0.0)
            )
        previous_start = history_end - timedelta(days=RECENT_TREND_DAYS * 2 - 1)
        recent_start = history_end - timedelta(days=RECENT_TREND_DAYS - 1)
        recent_total = sum(
            quantity for day, quantity in daily_sales[recipe_id].items()
            if recent_start <= day <= history_end
        )
        previous_total = sum(
            quantity for day, quantity in daily_sales[recipe_id].items()
            if previous_start <= day < recent_start
        )
        factor = (
            min(MAX_TREND_FACTOR, max(MIN_TREND_FACTOR, recent_total / previous_total))
            if previous_total > 0
            else 1.0
        )
        trend_factors[recipe_id] = factor
        forecasts[recipe_id] = {
            day: (
                sum(by_weekday.get(day.weekday(), []))
                / len(by_weekday.get(day.weekday(), [1]))
            ) * factor
            for day in forecast_days
        }
    return forecasts, len(distinct_sales_days), trend_factors


def _status_snapshot(
    restaurant_id: str,
    forecast_start: date,
    period_days: int,
) -> dict[str, dict[str, Any]]:
    forecast_key = f"{forecast_start.isoformat()}:{period_days}"
    return {
        str(record.get("ingredient_id")): record
        for record in db.query_collection(
            _path(restaurant_id, "purchase_recommendations"),
            [("forecast_key", "==", forecast_key)],
        )
    }


def get_purchase_recommendations(
    restaurant_id: str,
    forecast_period_days: int,
    as_of: date | None = None,
) -> PurchaseRecommendationDashboard:
    today = as_of or datetime.now(timezone.utc).date()
    forecast_start = today + timedelta(days=1)
    history_end = today - timedelta(days=1)
    history_start = history_end - timedelta(days=HISTORY_DAYS - 1)
    inventory = db.get_collection(_path(restaurant_id, "inventory_items"))
    recipe_documents = db.get_collection(_path(restaurant_id, "recipes"))
    recipe_ingredients = db.get_collection(_path(restaurant_id, "recipe_ingredients"))
    recipes = {
        str(recipe.get("recipe_id") or recipe.get("id")): recipe
        for recipe in recipe_documents
        if recipe.get("is_active", True)
    }
    sales = db.query_collection(
        _path(restaurant_id, "daily_sales"),
        [
            ("sale_date", ">=", history_start.isoformat()),
            ("sale_date", "<=", history_end.isoformat()),
        ],
    )
    data_warnings = []
    if not inventory:
        data_warnings.append("No inventory items are configured.")
    if not recipes:
        data_warnings.append("No active recipes are configured; menu sales cannot be translated into ingredient demand.")
    if not recipe_ingredients:
        data_warnings.append("No recipe ingredient rows are configured.")
    if not sales:
        data_warnings.append("No sales records were found in the 56-day history window; the page will not invent demand.")

    max_lead_time = max(
        (int(item.get("lead_time_days", 0) or 0) for item in inventory),
        default=0,
    )
    projection_days = min(90, forecast_period_days + max_lead_time)
    forecast_dates = [
        forecast_start + timedelta(days=offset)
        for offset in range(projection_days)
    ]
    recipe_forecasts, sales_day_count, trend_factors = _forecast_sales_by_recipe(
        sales, recipes, forecast_dates, history_start, history_end,
    )

    ingredient_ids = [
        str(item.get("ingredient_id") or item.get("id"))
        for item in inventory
    ]
    ingredients_by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in recipe_ingredients:
        recipe_id = str(row.get("recipe_id", ""))
        if recipe_id in recipes:
            ingredients_by_recipe[recipe_id].append(row)

    inventory_by_id = {
        str(item.get("ingredient_id") or item.get("id")): item
        for item in inventory
    }
    requirements: dict[str, list[tuple[str, float, str, str | None, list[str]]]] = defaultdict(list)
    warnings_by_ingredient: dict[str, list[str]] = defaultdict(list)
    for recipe_id, rows in ingredients_by_recipe.items():
        for row in rows:
            ingredient_id = str(row.get("ingredient_id", ""))
            try:
                item = inventory_by_id.get(ingredient_id)
                if item is None:
                    continue
                raw_per_portion, unit = raw_ingredient_quantity(
                    item,
                    float(row["required_quantity"]) / float(row["servings_per_batch"]),
                    str(row["required_unit"]),
                    str(row.get("required_stage") or "raw"),
                    row.get("yield_stage_reference"),
                )
                stages = item.get("yield_stages") or []
                applied_stages = []
                current_stage = "raw"
                for stage in stages:
                    if str(stage.get("input_stage", current_stage)).lower() != current_stage:
                        continue
                    applied_stages.append(
                        f"{stage.get('stage_name')} ({float(stage.get('yield_percentage', 0)):+g}%)"
                    )
                    current_stage = str(stage.get("output_stage") or stage.get("stage_name", "")).lower()
                    if current_stage == str(row.get("required_stage") or "raw").lower():
                        break
                requirements[ingredient_id].append((
                    recipe_id,
                    raw_per_portion,
                    unit,
                    row.get("yield_stage_reference"),
                    applied_stages,
                ))
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
                warnings_by_ingredient[ingredient_id].append(
                    f"Recipe {recipes[recipe_id].get('recipe_name', recipe_id)} cannot be converted to stock units: {error}"
                )

    recommendation_path = _path(restaurant_id, "purchase_recommendations")
    status_by_ingredient = _status_snapshot(restaurant_id, forecast_start, forecast_period_days)
    projection_end = forecast_dates[-1] if forecast_dates else forecast_start
    ordered_records = db.query_collection(
        recommendation_path,
        [
            ("expected_delivery_date", ">=", forecast_start.isoformat()),
            ("expected_delivery_date", "<=", projection_end.isoformat()),
        ],
    )
    incoming_by_ingredient: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in ordered_records:
        expected = _date(record.get("expected_delivery_date"))
        if expected and expected >= forecast_start and record.get("status") == "ordered":
            incoming_by_ingredient[str(record.get("ingredient_id"))].append(record)

    relevant_lines = []
    for offset in range(0, len(ingredient_ids), 30):
        relevant_lines.extend(db.query_collection(
            _path(restaurant_id, "purchase_lines"),
            [("ingredient_id", "in", ingredient_ids[offset:offset + 30])],
        ))
    invoice_ids = list(dict.fromkeys(
        str(line.get("purchase_id")) for line in relevant_lines if line.get("purchase_id")
    ))
    verified_invoices: set[str] = set()
    for offset in range(0, len(invoice_ids), 30):
        for invoice in db.query_collection(
            _path(restaurant_id, "purchase_invoices"),
            [("purchase_id", "in", invoice_ids[offset:offset + 30])],
        ):
            if invoice.get("verification_status") == "verified":
                verified_invoices.add(str(invoice.get("purchase_id")))
    lines_by_ingredient: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in relevant_lines:
        if str(line.get("purchase_id")) in verified_invoices:
            lines_by_ingredient[str(line.get("ingredient_id"))].append(line)

    active_recipe_ids_with_sales = {
        str(sale.get("recipe_id")) for sale in sales
        if float(sale.get("net_quantity_sold", 0) or 0) > 0
    }
    recipe_ids_without_sales = set(recipes) - active_recipe_ids_with_sales
    recommendations: list[PurchaseRecommendation] = []

    for item in inventory:
        ingredient_id = str(item.get("ingredient_id") or item.get("id"))
        unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
        current_stock = _item_stock(item)
        lot_warnings: list[str] = []
        if item.get("lot_tracking_enabled"):
            tracked_lines = lines_by_ingredient.get(ingredient_id, [])
            current_stock = max(0.0, float(item.get("untracked_stock_quantity", 0) or 0))
            for line in tracked_lines:
                remaining = line.get("remaining_usable_quantity")
                if remaining is None:
                    lot_warnings.append("Lot tracking is incomplete for one or more verified batches; only recorded lot balances and untracked stock are counted as usable.")
                    continue
                expiry = _date(line.get("expiry_date"))
                if expiry is None or expiry >= today:
                    current_stock += max(0.0, float(remaining))
            if item.get("untracked_stock_quantity", 0):
                lot_warnings.append("Some on-hand stock has no batch/expiry assignment and is counted as usable without expiry adjustment.")
        else:
            lot_warnings.append("Lot-level expiry tracking is not enabled; aggregate on-hand stock is used.")
        lead_time_raw = item.get("lead_time_days")
        lead_time = int(lead_time_raw) if lead_time_raw is not None else None
        lead_days = lead_time or 0
        safety_stock = max(0.0, float(item.get("safety_stock", 0) or 0))
        reorder_threshold = max(0.0, float(item.get("reorder_threshold", 0) or 0))
        threshold = max(safety_stock, reorder_threshold)
        daily_demand = {day: 0.0 for day in forecast_dates}
        sales_basis: list[RecommendationDemandBasis] = []
        for recipe_id, raw_per_portion, stock_unit, yield_reference, applied_stages in requirements.get(ingredient_id, []):
            if stock_unit.lower() != unit.lower():
                try:
                    raw_per_portion = convert_quantity(raw_per_portion, stock_unit, unit)
                except ValueError as error:
                    warnings_by_ingredient[ingredient_id].append(str(error))
                    continue
            portions_forecast = sum(
                recipe_forecasts.get(recipe_id, {}).get(day, 0.0)
                for day in forecast_dates[:forecast_period_days]
            )
            sales_basis.append(RecommendationDemandBasis(
                recipe_id=recipe_id,
                recipe_name=str(recipes[recipe_id].get("recipe_name", recipe_id)),
                forecast_portions=round(portions_forecast, 3),
                raw_quantity_per_portion=round(raw_per_portion, 6),
                trend_factor=round(trend_factors.get(recipe_id, 1.0), 3),
                unit=unit,
                yield_stages_applied=applied_stages,
            ))
            for day in forecast_dates:
                daily_demand[day] += (
                    recipe_forecasts.get(recipe_id, {}).get(day, 0.0) * raw_per_portion
                )

        incoming: list[RecommendationIncomingOrder] = []
        for record in incoming_by_ingredient.get(ingredient_id, []):
            expected = _date(record.get("expected_delivery_date"))
            if not expected:
                continue
            incoming.append(RecommendationIncomingOrder(
                recommendation_id=str(record["id"]),
                quantity=float(record.get("recommended_purchase_quantity", 0)),
                expected_delivery_date=expected,
                order_reference=str(record.get("order_reference") or "Manually recorded order"),
            ))

        projected_stock = current_stock
        stockout_date = None
        threshold_breach_date = None
        total_forecast_consumption = 0.0
        for day in forecast_dates:
            projected_stock += sum(
                order.quantity for order in incoming if order.expected_delivery_date == day
            )
            projected_stock -= daily_demand[day]
            total_forecast_consumption += daily_demand[day]
            if threshold_breach_date is None and projected_stock < threshold:
                threshold_breach_date = day
            if stockout_date is None and projected_stock <= 0:
                stockout_date = day

        order_date = (
            threshold_breach_date - timedelta(days=lead_days)
            if threshold_breach_date
            else None
        )
        order_due = bool(order_date and order_date <= today)
        total_incoming = sum(
            order.quantity for order in incoming
            if order.expected_delivery_date <= forecast_dates[-1]
        ) if forecast_dates else 0.0
        quantity = max(0.0, total_forecast_consumption + threshold - current_stock - total_incoming)
        min_order = item.get("minimum_order_quantity")
        pack_size = item.get("pack_size")
        if quantity > 0 and min_order is not None:
            quantity = max(quantity, float(min_order))
        if quantity > 0 and pack_size is not None:
            pack_size = float(pack_size)
            if pack_size <= 0:
                warnings_by_ingredient[ingredient_id].append("Pack size must be greater than zero; order quantity is not rounded.")
            else:
                quantity = math.ceil((quantity - 1e-9) / pack_size) * pack_size
        has_sales_basis = any(
            recipe_id in active_recipe_ids_with_sales
            for recipe_id, *_ in requirements.get(ingredient_id, [])
        )
        if not has_sales_basis:
            quantity = 0.0
        quantity = round(quantity, 4)

        warnings = [*lot_warnings, *warnings_by_ingredient.get(ingredient_id, [])]
        if sales_day_count < 14:
            warnings.append(f"Only {sales_day_count} distinct sales days were found in the 56-day history window.")
        if not requirements.get(ingredient_id):
            warnings.append("No active recipe ingredient rows link this ingredient to menu demand.")
        if any(recipe_id in recipe_ids_without_sales for recipe_id, *_ in requirements.get(ingredient_id, [])):
            warnings.append("Some active recipes have no sales in the history window; forecast completeness may be limited.")
        if lead_time is None or lead_time <= 0:
            warnings.append("Supplier lead time is missing or zero; order timing cannot be reliably estimated.")
        if not item.get("supplier_id"):
            warnings.append("Supplier is not configured for this ingredient.")
        if min_order is None:
            warnings.append("Minimum order quantity is not configured; quantity uses the exact calculated requirement.")
        if pack_size is None:
            warnings.append("Pack size is not configured; quantity is not rounded to a supplier pack.")
        expired_or_near_expiry = []
        for line in lines_by_ingredient.get(ingredient_id, []):
            expiry = _date(line.get("expiry_date"))
            if not expiry:
                continue
            remaining_quantity = max(0.0, float(line.get("remaining_usable_quantity", 0) or 0))
            if expiry <= today + timedelta(days=60) and (expiry < today or remaining_quantity > 0):
                expired_or_near_expiry.append(RecommendationExpiryBatch(
                    purchase_id=str(line.get("purchase_id", "")),
                    batch_number=line.get("batch_number"),
                    expiry_date=expiry,
                    quantity_received=float(line.get("ingredient_quantity_received", line.get("quantity_received", 0))),
                    remaining_usable_quantity=remaining_quantity,
                    expired=expiry < today,
                    unit=str(line.get("usable_unit") or line.get("purchase_unit") or unit),
                ))
        if any(batch.expired and batch.remaining_usable_quantity > 0 for batch in expired_or_near_expiry):
            warnings.append("Expired batch balances are excluded from usable stock. Record a waste/write-off for expired physical stock to reconcile aggregate inventory.")
        if expired_or_near_expiry:
            warnings.append("Batch expiry and remaining quantities are displayed from verified purchase lots.")
        if sales_day_count < 14 or not requirements.get(ingredient_id) or warnings_by_ingredient.get(ingredient_id):
            reliability = "low"
        elif sales_day_count < 28 or lead_time is None or lead_time <= 0:
            reliability = "medium"
        else:
            reliability = "baseline"

        status_record = status_by_ingredient.get(ingredient_id, {})
        status = str(status_record.get("status") or ("needs_review" if quantity > 0 else "no_action"))
        if quantity > 0:
            if order_due:
                priority = "critical"
            elif threshold_breach_date and threshold_breach_date <= today + timedelta(days=lead_days + 2):
                priority = "high"
            elif threshold_breach_date:
                priority = "medium"
            else:
                priority = "low"
        else:
            priority = "low"
        estimated_cost = (
            round(quantity * float(item.get("unit_cost", item.get("unit_cost_inr", 0))), 2)
            if item.get("unit_cost", item.get("unit_cost_inr")) is not None
            else None
        )
        forecast_daily_average = (
            sum(daily_demand[day] for day in forecast_dates[:forecast_period_days])
            / forecast_period_days
        )
        explanation = (
            f"Baseline: average net portions sold for each weekday over {HISTORY_DAYS} days, "
            f"with per-recipe trend bounded to {MIN_TREND_FACTOR:.1f}–{MAX_TREND_FACTOR:.1f}x. "
            f"Recipe quantities were divided by batch servings and converted once to raw stock units. "
            f"Recorded inventory is {current_stock:g} {unit}; confirmed incoming orders due in the "
            f"projection are {total_incoming:g} {unit}. Projected consumption over {len(forecast_dates)} "
            f"days is {total_forecast_consumption:g} {unit}; reorder buffer (max of threshold and safety "
            f"stock) is {threshold:g} {unit}. The calculated order quantity is forecast consumption + "
            f"reorder buffer - current stock - "
            f"confirmed incoming, then supplier minimum and pack-size constraints are applied. "
            f"Forecast quality: {reliability}."
        )
        recommendations.append(PurchaseRecommendation(
            recommendation_id=_recommendation_id(forecast_start, forecast_period_days, ingredient_id),
            ingredient_id=ingredient_id,
            ingredient_name=str(item.get("item_name", ingredient_id)),
            forecast_start_date=forecast_start,
            forecast_period_days=forecast_period_days,
            current_usable_stock=current_stock,
            stock_unit=unit,
            stock_source="Current inventory on-hand quantity; batch-level remaining quantities are not tracked.",
            forecast_daily_consumption=round(forecast_daily_average, 4),
            reorder_threshold=reorder_threshold,
            safety_stock=safety_stock,
            supplier_id=item.get("supplier_id"),
            supplier_lead_time_days=lead_time,
            projected_stockout_date=stockout_date,
            recommended_order_date=order_date,
            recommended_purchase_quantity=quantity,
            estimated_purchase_cost=estimated_cost,
            priority=priority,
            status=status,
            explanation=explanation,
            reliability_warnings=warnings,
            demand_forecast={
                day.isoformat(): round(daily_demand[day], 4)
                for day in forecast_dates
            },
            sales_basis=sales_basis,
            incoming_orders=incoming,
            expiry_batches=sorted(expired_or_near_expiry, key=lambda record: record.expiry_date),
            expected_delivery_date=_date(status_record.get("expected_delivery_date")),
            order_reference=status_record.get("order_reference"),
            purchase_line_id=status_record.get("purchase_line_id"),
        ))

    visible = [
        recommendation for recommendation in recommendations
        if recommendation.recommended_purchase_quantity > 0
        or recommendation.status in {"approved", "ordered", "received"}
    ]
    visible.sort(key=lambda recommendation: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}[recommendation.priority],
        recommendation.recommended_order_date or date.max,
        recommendation.projected_stockout_date or date.max,
        recommendation.ingredient_name.casefold(),
    ))
    return PurchaseRecommendationDashboard(
        forecast_period_days=forecast_period_days,
        forecast_start_date=forecast_start,
        generated_at=datetime.now(timezone.utc).isoformat(),
        ingredients_requiring_replenishment=sum(
            recommendation.recommended_purchase_quantity > 0 for recommendation in recommendations
        ),
        upcoming_stockout_risks=sum(
            recommendation.projected_stockout_date is not None for recommendation in recommendations
        ),
        recommendations_awaiting_approval=sum(
            recommendation.recommended_purchase_quantity > 0 and recommendation.status == "needs_review"
            for recommendation in recommendations
        ),
        data_warnings=data_warnings,
        recommendations=visible,
    )


def update_recommendation_status(
    restaurant_id: str,
    recommendation_id: str,
    update: RecommendationStatusUpdate,
) -> dict[str, Any]:
    expected_id = _recommendation_id(
        update.forecast_start_date,
        update.forecast_period_days,
        update.ingredient_id,
    )
    if recommendation_id != expected_id:
        raise ValueError("Recommendation identifier does not match its forecast period and ingredient.")
    collection_path = _path(restaurant_id, "purchase_recommendations")
    current = db.get_document(collection_path, recommendation_id)
    current_status = str(current.get("status")) if current else None
    transitions = {
        ("needs_review", "approved"): "approved",
        ("approved", "ordered"): "ordered",
        ("ordered", "received"): "received",
    }
    if current_status is None and update.status == "approved":
        previous_status = None
    else:
        previous_status = next(
            (previous for (previous, following) in transitions if following == update.status and previous == current_status),
            None,
        )
    if update.status == "approved" and current_status == "needs_review":
        previous_status = "needs_review"
    if previous_status is None and not (current_status is None and update.status == "approved"):
        raise ValueError("Recommendation status transition is not allowed; refresh the forecast.")

    extra: dict[str, Any] = {}
    if update.status == "approved":
        snapshot = get_purchase_recommendations(
            restaurant_id,
            update.forecast_period_days,
            update.forecast_start_date - timedelta(days=1),
        )
        recommendation = next(
            (row for row in snapshot.recommendations if row.recommendation_id == recommendation_id),
            None,
        )
        if recommendation is None:
            raise ValueError("Recommendation is no longer available; refresh the forecast.")
        extra["recommended_purchase_quantity"] = recommendation.recommended_purchase_quantity
    if update.status == "ordered":
        if not update.order_reference or not update.expected_delivery_date:
            raise ValueError("An order reference and expected delivery date are required to mark it ordered.")
        extra.update({
            "order_reference": update.order_reference.strip(),
            "expected_delivery_date": update.expected_delivery_date.isoformat(),
        })
    if update.status == "received":
        if not update.purchase_line_id:
            raise ValueError("A verified purchase line is required to mark the recommendation received.")
        line = db.get_document(_path(restaurant_id, "purchase_lines"), update.purchase_line_id)
        if not line or str(line.get("ingredient_id")) != update.ingredient_id:
            raise ValueError("Purchase line does not match this recommendation ingredient.")
        invoice = db.get_document(_path(restaurant_id, "purchase_invoices"), str(line.get("purchase_id", "")))
        if not invoice or invoice.get("verification_status") != "verified":
            raise ValueError("The linked purchase invoice must be verified before marking received.")
        prior_links = db.query_collection(
            collection_path,
            [("purchase_line_id", "==", update.purchase_line_id)],
        )
        if any(record.get("id") != recommendation_id for record in prior_links):
            raise ValueError("This purchase line is already linked to another recommendation.")
        extra["purchase_line_id"] = update.purchase_line_id

    forecast_key = f"{update.forecast_start_date.isoformat()}:{update.forecast_period_days}"
    data = {
        **(current or {}),
        "id": recommendation_id,
        "recommendation_id": recommendation_id,
        "ingredient_id": update.ingredient_id,
        "forecast_start_date": update.forecast_start_date.isoformat(),
        "forecast_period_days": update.forecast_period_days,
        "forecast_key": forecast_key,
        "status": update.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    db.transition_document(collection_path, recommendation_id, previous_status, data)
    return data
