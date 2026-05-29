from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.app.api.routes import router
# Domain-specific routers (extracted from routes.py — activate once old
# endpoints are removed from routes.py to avoid route conflicts):
# from src.backend.app.api.dpabi_routes import router as dpabi_router
# from src.backend.app.api.rsfmri_routes import router as rsfmri_router
# from src.backend.app.api.agent_routes import router as agent_router
from src.backend.app.api.dashboard_routes import router as dashboard_router
from src.backend.app.api.desktop_routes import router as desktop_router
from src.backend.app.api.external_smoke_routes import router as external_smoke_router
from src.backend.app.api.gui_agent_routes import router as gui_agent_router
from src.backend.app.api.plan_validator_routes import router as plan_validator_router
from src.backend.app.api.planner_routes import router as planner_router
from src.backend.app.api.tool_catalog_routes import router as tool_catalog_router
from src.backend.app.version import API_DESCRIPTION, API_TITLE, APP_VERSION


def create_app() -> FastAPI:
    app = FastAPI(
        title=API_TITLE,
        version=APP_VERSION,
        description=API_DESCRIPTION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(dashboard_router)
    app.include_router(planner_router)
    app.include_router(tool_catalog_router)
    app.include_router(plan_validator_router)
    app.include_router(gui_agent_router)
    app.include_router(desktop_router)
    app.include_router(external_smoke_router)
    return app


app = create_app()
