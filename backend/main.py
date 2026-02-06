"""FastAPI application entry point."""

import sys
from pathlib import Path

# Ensure backend is on the path (same convention as tests/conftest.py)
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database import init_db
from api.routes_game import router as game_router
from api.routes_forecast import router as forecast_router
from api.routes_recommend import router as recommend_router

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


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
