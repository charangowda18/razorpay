"""
AI Revenue Recovery System — Main Entry Point

FastAPI application that serves both the REST API and the frontend dashboard.

Architecture:
    Frontend (HTML/CSS/JS) ← served as static files
    ↕ REST API
    FastAPI Backend
    ↕
    SQLite DB + ML Model + Gemini LLM
"""

import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import init_database
from routers import transactions, recovery, analytics

# ============================================================
# App Setup
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered payment recovery system that detects failed payments, "
        "predicts retry success using ML, and generates recovery strategies using LLM."
    ),
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc at /redoc
)

# CORS — allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Register API Routers
# ============================================================

app.include_router(transactions.router)
app.include_router(recovery.router)
app.include_router(analytics.router)

# ============================================================
# Static Files (Frontend)
# ============================================================

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# ============================================================
# Root Routes
# ============================================================

@app.get("/")
async def serve_frontend():
    """Serve the frontend dashboard."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": "/docs",
        "api_endpoints": {
            "dashboard": "/api/analytics/dashboard",
            "failed_transactions": "/api/transactions/failed",
            "recovery_opportunities": "/api/recovery/opportunities",
            "ai_insights": "/api/recovery/insights",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from services.ai_agent import is_available as ai_available

    ml_available = False
    try:
        from ml.predict import get_model_info
        get_model_info()
        ml_available = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "ai_available": ai_available(),
        "ml_model_loaded": ml_available,
    }


# ============================================================
# Startup Event
# ============================================================

@app.on_event("startup")
async def startup():
    """Initialize database and preload ML model on startup."""
    init_database()

    # Preload ML model into memory so first request is instant
    try:
        from ml.predict import _load_model
        _load_model()
        print("[OK] ML model preloaded.")
    except Exception as e:
        print(f"[WARN] ML model not preloaded: {e}")

    print(f"\n* {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  Dashboard: http://localhost:8000")
    print(f"  API Docs:  http://localhost:8000/docs")
    print(f"  AI Agent:  {'Connected' if settings.GEMINI_API_KEY else 'No API key'}")
    print()

    # Auto-open browser
    import webbrowser
    webbrowser.open("http://localhost:8000")
