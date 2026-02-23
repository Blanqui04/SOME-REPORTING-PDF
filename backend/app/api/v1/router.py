"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.grafana import router as grafana_router
from backend.app.api.v1.reports import router as reports_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(grafana_router)
v1_router.include_router(reports_router)
