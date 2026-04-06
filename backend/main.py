"""
main.py — PixelForge FastAPI backend

Run from project root:
    py -3.12 -m uvicorn backend.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routes import render, refine, mesh

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "output"
ASSETS_DIR   = PROJECT_ROOT / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure output directories exist on startup
    (OUTPUT_DIR / "frames").mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="PixelForge API",
    description="8-directional isometric sprite sheet generation pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(render.router)
app.include_router(refine.router)
app.include_router(mesh.router)

# Serve output PNGs as static files: /output/sprite_sheet.png etc.
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
# Serve uploaded assets: /assets/my_mesh.glb etc.
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
