import sys
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings
from backend.app.db.sql import get_db
from backend.app.db.neo4j import check_neo4j_health

app = FastAPI(
    title="Case Connect AI | Backend API",
    description="Investigation support system for law enforcement (SIH26189 | Team UNITx)",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG or True else None,
    redoc_url=None
)

# Mandatory HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:;"
    return response

# Strict CORS configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "project": "Case Connect AI",
        "description": "Crime Network Analysis System",
        "team": "UNITx",
        "status": "online",
        "legal_standard": "Section 63 BSA 2023",
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # 1. SQLite Health Check
    sqlite_status = "error"
    try:
        db.execute(text("SELECT 1"))
        sqlite_status = "ok"
    except Exception as e:
        sqlite_status = f"error: {str(e)}"

    # 2. Neo4j Health Check
    neo4j_healthy = check_neo4j_health()
    neo4j_status = "ok" if neo4j_healthy else "unreachable"

    overall_status = "healthy" if sqlite_status == "ok" and neo4j_healthy else "degraded"
    if sqlite_status == "ok" and not neo4j_healthy:
        overall_status = "sqlite_online_neo4j_offline"

    return {
        "status": overall_status,
        "sqlite": sqlite_status,
        "neo4j": neo4j_status,
        "version": "1.0.0"
    }

# Register Feature Routers
from backend.app.auth.router import router as auth_router
from backend.app.cases.router import router as cases_router
from backend.app.evidence.router import router as evidence_router
from backend.app.audit.router import router as audit_router
from backend.app.services.ingestion.router import router as ingestion_router
from backend.app.services.graph.router import router as graph_router
from backend.app.services.money.router import router as money_router
from backend.app.services.extraction.router import router as extraction_router
from backend.app.services.reports.router import router as reports_router
from backend.app.services.analytics.router import router as analytics_router
from backend.app.services.matching.router import router as matching_router
from backend.app.services.ai.router import router as ai_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(cases_router, prefix="/cases", tags=["Cases"])
app.include_router(evidence_router, tags=["Evidence"])
app.include_router(audit_router, prefix="/audit", tags=["Audit"])
app.include_router(ingestion_router, tags=["Ingestion"])
app.include_router(graph_router, tags=["Graph"])
app.include_router(money_router, tags=["Money Trail"])
app.include_router(extraction_router, tags=["Document Extraction"])
app.include_router(reports_router, tags=["Reports & Dossier"])
app.include_router(analytics_router, tags=["Analytics & Lead Advisor"])
app.include_router(matching_router, tags=["Entity Matching & Master Profiles"])
app.include_router(ai_router, tags=["AI & Gemini Copilot"])



