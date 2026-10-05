import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import crud, models
from app.database import SessionLocal, engine
from app.routers import reservations, restaurants

# Create tables on startup
models.Base.metadata.create_all(bind=engine)

# Seed demo data if database is fresh
with SessionLocal() as db:
    crud.seed_demo_data(db)

app = FastAPI(
    title="Tablekeeper API",
    description="Production-grade Autonomous Table Reservation Platform for Dark Factory",
    version="1.0.0",
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Tablekeeper", "version": "1.0.0"}


# Include API routers
app.include_router(restaurants.router)
app.include_router(reservations.router)

# Serve static frontend files if static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
