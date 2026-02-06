"""FastAPI application entry point."""

import sys
import logging
from pathlib import Path

# Ensure backend is on the path (same convention as tests/conftest.py)
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from db.database import init_db
from api.routes_game import router as game_router
from api.routes_forecast import router as forecast_router
from api.routes_recommend import router as recommend_router

logger = logging.getLogger(__name__)

app = FastAPI(title="WHOP — Workflow-guided Hospital Outcomes Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)
app.include_router(forecast_router)
app.include_router(recommend_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON for all unhandled exceptions instead of FastAPI's default HTML."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
