"""FastAPI application entry point.

Wires up:
- Lifespan (Redis connect/disconnect)
- CORS middleware
- Rate limiting (slowapi)
- Centralized JSON error handling
- Structured logging
- All routers
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.redis_client import close_redis, ping_redis
from app.routers import admin, auth, bookings, movies, payments, shows

# ── Structured Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify Redis.  Shutdown: close Redis pool."""
    logger.info("Starting up — pinging Redis...")
    try:
        await ping_redis()
        logger.info("Redis connected ✓")
    except Exception as e:
        logger.warning("Redis unavailable at startup: %s", e)
    yield
    logger.info("Shutting down — closing Redis...")
    await close_redis()


# ── App Factory ──
app = FastAPI(
    title=settings.APP_NAME,
    description="Movie Ticket Booking System — portfolio backend project",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate Limiting ──
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Centralized Error Handling ──
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Register Routers ──
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(movies.router)
app.include_router(shows.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# ── Static Files & Frontend ──
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

