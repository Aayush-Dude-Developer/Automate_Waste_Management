from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_restaurant_id
from ..schemas.stock import (
    MonthlyStockBalance,
    PhysicalStocktake,
    PurchaseInvoiceCreate,
    PurchaseInvoiceResponse,
    RecipeCreate,
    RecipeResponse,
    SaleCreate,
    SaleResponse,
    StaffConsumptionCreate,
    StaffConsumptionResponse,
    TheoreticalConsumption,
    WasteRecordCreateV2,
    WasteRecordResponseV2,
)
from ..schemas.purchase_recommendations import (
    PurchaseRecommendationDashboard,
    RecommendationStatusUpdate,
)
from ..services import stock_service
from ..services import purchase_recommendation_service
from ..repositories.database import db

router = APIRouter(tags=["Stock, Purchases, Recipes & Sales"])


def _run(operation, *args):
    try:
        return operation(*args)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _validate_month(month: str):
    try:
        if len(month) != 7 or date.fromisoformat(f"{month}-01").strftime("%Y-%m") != month:
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Month must use YYYY-MM format.") from error


@router.get(
    "/api/purchase-recommendations",
    response_model=PurchaseRecommendationDashboard,
    tags=["Purchase Recommendations"],
)
def get_purchase_recommendations(
    forecast_period_days: int = Query(default=7, ge=1, le=28),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return purchase_recommendation_service.get_purchase_recommendations(
        restaurant_id,
        forecast_period_days,
    )


@router.patch(
    "/api/purchase-recommendations/{recommendation_id}/status",
    tags=["Purchase Recommendations"],
)
def update_purchase_recommendation_status(
    recommendation_id: str,
    update: RecommendationStatusUpdate,
    restaurant_id: str = Depends(get_restaurant_id),
):
    try:
        return purchase_recommendation_service.update_recommendation_status(
            restaurant_id,
            recommendation_id,
            update,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/purchases", response_model=PurchaseInvoiceResponse)
def create_purchase(
    purchase: PurchaseInvoiceCreate,
    restaurant_id: str = Depends(get_restaurant_id),
):
    return _run(stock_service.create_purchase, restaurant_id, purchase)


@router.get("/api/purchases", response_model=List[PurchaseInvoiceResponse])
def get_purchases(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return stock_service.get_purchases(restaurant_id, limit)


@router.post("/api/purchases/{purchase_id}/verify", response_model=PurchaseInvoiceResponse)
def verify_purchase(purchase_id: str, restaurant_id: str = Depends(get_restaurant_id)):
    return _run(stock_service.verify_purchase, restaurant_id, purchase_id)


@router.post("/api/recipes", response_model=RecipeResponse)
def create_recipe(recipe: RecipeCreate, restaurant_id: str = Depends(get_restaurant_id)):
    return _run(stock_service.create_recipe, restaurant_id, recipe)


@router.get("/api/recipes", response_model=List[RecipeResponse])
def get_recipes(restaurant_id: str = Depends(get_restaurant_id)):
    return stock_service.get_recipes(restaurant_id)


@router.post("/api/sales", response_model=SaleResponse)
def create_sale(sale: SaleCreate, restaurant_id: str = Depends(get_restaurant_id)):
    return _run(stock_service.create_sale, restaurant_id, sale)


@router.get("/api/sales", response_model=List[SaleResponse])
def get_sales(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return [
        SaleResponse(**record)
        for record in db.query_collection(
            f"restaurants/{restaurant_id}/daily_sales",
            order_by=("sale_date", "DESCENDING") if limit else None,
            limit=limit,
        )
    ]


@router.post("/api/staff-consumptions", response_model=StaffConsumptionResponse)
def create_staff_consumption(
    consumption: StaffConsumptionCreate,
    restaurant_id: str = Depends(get_restaurant_id),
):
    return _run(stock_service.create_staff_consumption, restaurant_id, consumption)


@router.get("/api/staff-consumptions", response_model=List[StaffConsumptionResponse])
def get_staff_consumptions(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return [
        StaffConsumptionResponse(**record)
        for record in db.query_collection(
            f"restaurants/{restaurant_id}/staff_consumptions",
            order_by=("consumption_date", "DESCENDING") if limit else None,
            limit=limit,
        )
    ]


@router.post("/api/stock/waste-records", response_model=WasteRecordResponseV2)
def create_waste_record(
    waste: WasteRecordCreateV2,
    restaurant_id: str = Depends(get_restaurant_id),
):
    return _run(stock_service.create_waste_record_v2, restaurant_id, waste)


@router.get("/api/stock/waste-records", response_model=List[WasteRecordResponseV2])
def get_waste_records_v2(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return [
        WasteRecordResponseV2(**record)
        for record in db.query_collection(
            f"restaurants/{restaurant_id}/waste_records_v2",
            order_by=("waste_date", "DESCENDING") if limit else None,
            limit=limit,
        )
    ]


@router.get("/api/stock-balances/{month}", response_model=List[MonthlyStockBalance])
def get_stock_balances(month: str, restaurant_id: str = Depends(get_restaurant_id)):
    _validate_month(month)
    return stock_service.get_monthly_balances(restaurant_id, month)


@router.post(
    "/api/stock-balances/{month}/{ingredient_id}/stocktake",
    response_model=MonthlyStockBalance,
)
def record_stocktake(
    month: str,
    ingredient_id: str,
    stocktake: PhysicalStocktake,
    restaurant_id: str = Depends(get_restaurant_id),
):
    _validate_month(month)
    return _run(stock_service.record_stocktake, restaurant_id, ingredient_id, month, stocktake)


@router.get(
    "/api/theoretical-consumption/{month}",
    response_model=List[TheoreticalConsumption],
)
def get_theoretical_consumption(
    month: str,
    restaurant_id: str = Depends(get_restaurant_id),
):
    _validate_month(month)
    return _run(stock_service.get_theoretical_consumption, restaurant_id, month)
