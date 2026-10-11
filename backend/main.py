from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, health, inventory, waste, documents, planning, ai, donations, analytics

app = FastAPI(
    title="SustainBite / Taiken Ops API",
    description="Food Waste Management and Inventory Optimization API",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(inventory.router)
app.include_router(waste.router)
app.include_router(documents.router)
app.include_router(planning.router)
app.include_router(ai.router)
app.include_router(donations.router)
app.include_router(analytics.router)
