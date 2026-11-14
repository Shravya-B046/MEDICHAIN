import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the Backend directory containing 'app' is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import (
    assistant_router,
    emergency_router,
    hospitals_router,
    reports_router,
    resources_router,
)
from app.services.emergency_service import seed_default_emergencies
from app.services.hospital_service import seed_sample_hospitals
from app.services.resource_service import seed_default_resources

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medichain")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    Auto-creates database tables and seeds synthetic demo data on start.
    """
    logger.info("Initializing database schema and seed data...")
    try:
        # Create all tables using SQLAlchemy 2.x engine
        Base.metadata.create_all(bind=engine)

        # Seed initial synthetic demo data if tables are empty
        db = SessionLocal()
        try:
            seed_sample_hospitals(db)
            seed_default_resources(db)
            seed_default_emergencies(db)
            logger.info("Database initialized with synthetic demo data.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error initializing database during startup: {e}")

    yield

    logger.info("MEDICHAIN backend application shutdown.")


# Create FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=(
        "MEDICHAIN AI-Powered Healthcare Coordination & Prediction Platform API. "
        "Provides endpoints for AI Health Assistance, Hospital Resource Visibility, "
        "Emergency Coordination, Preliminary Report Analysis, and Facility Administration."
    ),
    lifespan=lifespan,
)

# Configure CORS Middleware for Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Feature Routers under /api
app.include_router(hospitals_router)
app.include_router(resources_router)
app.include_router(emergency_router)
app.include_router(reports_router)
app.include_router(assistant_router)


@app.get("/", tags=["Health"])
def root_status():
    """Root endpoint verifying API availability and active core modules."""
    return {
        "status": "online",
        "platform": "MEDICHAIN",
        "description": "AI-Powered Healthcare Coordination & Prediction Platform",
        "version": settings.PROJECT_VERSION,
        "docs_url": "/docs",
        "modules": [
            "AI Health Assistant (/api/assistant)",
            "Hospital Resource Dashboard (/api/resources)",
            "Emergency Coordination (/api/emergency)",
            "AI Preliminary Report Analysis (/api/reports)",
            "Hospital Management & Administration (/api/hospitals)",
        ],
        "demo_data_notice": (
            "All figures and responses in prototype mode represent synthetic demo data. "
            "Not connected to live emergency services."
        ),
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health-check endpoint for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "database": "operational",
        "environment": settings.ENVIRONMENT,
    }

