"""
SaralPolicy - Local AI Insurance Analysis
POC/Demo system with bilingual UI, working TTS, and human-readable formatting.
Architecture: Modular Service-Based (Decoupled from Monolith)

Status: POC/Demo - Not production ready
See docs/reports/PRODUCTION_ENGINEERING_EVALUATION.md for assessment.
"""

# Load environment variables from .env file BEFORE any other imports
# This ensures HF_TOKEN and other secrets are available to all modules
from dotenv import load_dotenv
load_dotenv()  # Loads from backend/.env (never committed to repo)

import os
import time
from pathlib import Path
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

# Import Configuration (validates at import time)
from app.config import get_settings, AppSettings

# Import Service Initializer
from app.dependencies import init_services

# Import Routes
from app.routes import health, tts, translation, analysis

# Import Middleware
from app.middleware.input_validation import InputValidationMiddleware
from app.middleware.cors_validation import get_validated_origins

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# =============================================================================
# LIFESPAN EVENT HANDLER (Modern FastAPI pattern)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info("🚀 SaralPolicy Backend Starting Up...")
    
    # Validate configuration at startup (fail-fast)
    try:
        settings = get_settings()
        logger.info(
            "✅ Configuration validated",
            environment=settings.environment,
            ollama_model=settings.ollama.model,
        )
    except Exception as e:
        logger.error("❌ Configuration validation failed", error=str(e))
        raise RuntimeError(f"Invalid configuration: {e}")
    
    init_services()
    logger.info("✅ Services Initialized.")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 SaralPolicy Backend Shutting Down...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="SaralPolicy",
    description="AI-powered insurance document analysis with local privacy",
    version="2.1.0",
    lifespan=lifespan
)

# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS - Validated at startup for security
# See app/middleware/cors_validation.py for security documentation
ALLOWED_ORIGINS = get_validated_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Rate Limiting
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter to prevent DoS attacks."""
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        minute_ago = current_time - 60
        # Clean old entries
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > minute_ago]
        
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response("Rate limit exceeded.", status_code=429)
            
        self.requests[client_ip].append(current_time)
        return await call_next(request)

# Security Headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "media-src 'self' blob:;"
        )
        return response

app.add_middleware(RateLimitMiddleware, requests_per_minute=get_settings().rate_limit.requests_per_minute)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputValidationMiddleware)  # Validate input size to prevent DoS

# =============================================================================
# ROUTES
# =============================================================================

app.include_router(health.router)
app.include_router(tts.router)
app.include_router(translation.router)

app.include_router(analysis.router) # Now handles /upload and /ask_document

# =============================================================================
# STATIC / FRONTEND ROUTES
# =============================================================================

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/favicon.ico")
async def favicon():
    favicon_path = Path("static/favicon.ico")
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    privacy_html = Path("templates/privacy.html")
    if privacy_html.exists():
        return privacy_html.read_text(encoding='utf-8')
    return HTMLResponse("<h1>Privacy Policy</h1><p>Coming soon.</p>")

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = Path("templates/index.html")
    if html_content.exists():
        return html_content.read_text(encoding='utf-8')
    return "<h1>SaralPolicy AI (Backend Running)</h1>" # Minimal fallback


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
