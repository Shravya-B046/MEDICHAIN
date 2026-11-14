from app.routers.hospitals import router as hospitals_router
from app.routers.resources import router as resources_router
from app.routers.emergency import router as emergency_router
from app.routers.reports import router as reports_router
from app.routers.assistant import router as assistant_router

__all__ = [
    "hospitals_router",
    "resources_router",
    "emergency_router",
    "reports_router",
    "assistant_router",
]

