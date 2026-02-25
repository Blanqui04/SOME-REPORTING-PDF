"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.grafana import router as grafana_router
from backend.app.api.v1.i18n import router as i18n_router
from backend.app.api.v1.organizations import router as orgs_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.schedules import router as schedules_router
from backend.app.api.v1.templates import router as templates_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(alerts_router)
v1_router.include_router(audit_router)
v1_router.include_router(auth_router)
v1_router.include_router(grafana_router)
v1_router.include_router(i18n_router)
v1_router.include_router(orgs_router)
v1_router.include_router(reports_router)
v1_router.include_router(schedules_router)
v1_router.include_router(templates_router)
