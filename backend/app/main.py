import sys
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings
from backend.app.db.sql import Base, engine, SessionLocal, User, get_db
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "connect-src 'self' ws: wss: https: http:;"
    )
    return response

# Strict CORS configuration supporting Local, Docker and Cloud Deployments
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:80",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.railway\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup_lifecycle():
    """Ensure database tables and initial officer credentials exist automatically."""
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from scripts.seed_users import hash_password
            users_to_seed = [
                ("admin", "admin", "AdminPass1234!"),
                ("investigator1", "investigator", "OfficerPass1234!"),
                ("viewer1", "viewer", "ViewerPass1234!")
            ]
            for uname, urole, upass in users_to_seed:
                if not db.query(User).filter(User.username == uname).first():
                    db.add(User(username=uname, role=urole, password_hash=hash_password(upass), is_active=True))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[STARTUP WARNING] DB init/seed exception: {e}")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@app.get("/")
def read_root(request: Request):
    accept = request.headers.get("accept", "")
    is_browser = "text/html" in accept or request.headers.get("sec-fetch-dest") == "document"
    if is_browser and frontend_dist.exists() and (frontend_dist / "index.html").exists():
        return FileResponse(str(frontend_dist / "index.html"))
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

feature_routers = [
    (auth_router, "/auth", ["Auth"]),
    (cases_router, "/cases", ["Cases"]),
    (evidence_router, "", ["Evidence"]),
    (audit_router, "/audit", ["Audit"]),
    (ingestion_router, "", ["Ingestion"]),
    (graph_router, "", ["Graph"]),
    (money_router, "", ["Money Trail"]),
    (extraction_router, "", ["Document Extraction"]),
    (reports_router, "", ["Reports & Dossier"]),
    (analytics_router, "", ["Analytics & Lead Advisor"]),
    (matching_router, "", ["Entity Matching & Master Profiles"]),
    (ai_router, "", ["AI & Gemini Copilot"]),
]

for rtr, pfx, tags in feature_routers:
    app.include_router(rtr, prefix=pfx, tags=tags)
    api_pfx = f"/api{pfx}" if pfx else "/api"
    app.include_router(rtr, prefix=api_pfx, tags=[f"API - {tags[0]}"])

# Unified Frontend SPA Serving for Render/Production Single-Service Deployments
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    async def serve_spa_frontend(request: Request, full_path: str):
        if (
            full_path == "api" or
            full_path.startswith("api/") or
            full_path.startswith("docs") or
            full_path.startswith("openapi.json") or
            full_path.startswith("health")
        ):
            return Response(status_code=404)
        if request.method not in ["GET", "HEAD"]:
            return Response(status_code=404)
        target = frontend_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(frontend_dist / "index.html"))




