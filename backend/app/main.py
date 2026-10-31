# OWNER: P1
import importlib
import logging
import pkgutil
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.clock import now
from app.core.config import settings
from app.core.db import init_db
from app.core.errors import (
    FestOSError,
    festos_exception_handler,
    generic_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.core.registry import iter_public_modules

logger = logging.getLogger("festos.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    try:
        init_db()
        if settings.SEED_ON_START:
            from app.seed.registry import run_seeders
            run_seeders(reset=False)
    except Exception as e:
        logger.warning(f"Startup DB init warning: {e}")
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="FestOS API",
    description="Internal command centre for the Aarohan fest (EPINOIA 2026, IIM Indore)",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# -------------------------------------------------------------
# 1. Request ID Middleware
# -------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# -------------------------------------------------------------
# 2. CORS Middleware
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 3. Exception Handlers
# -------------------------------------------------------------
app.add_exception_handler(FestOSError, festos_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# -------------------------------------------------------------
# 4. Standard Health & Meta Endpoints
# -------------------------------------------------------------
@app.get("/health", tags=["System"])
def get_health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "now": now().isoformat()
    }

# V1 Root Router
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/meta", tags=["System"])
def get_meta():
    modules = [m["slug"] for m in iter_public_modules()]
    return {
        "version": "0.1.0",
        "now": now().isoformat(),
        "modules": modules,
        "auth_disabled": settings.AUTH_DISABLED,
        "feature_flags": {
            "premortem": settings.ENABLE_PREMORTEM,
            "commands": settings.ENABLE_COMMANDS,
            "forecasting": settings.ENABLE_FORECASTING,
        },
    }

# -------------------------------------------------------------
# 5. Auto-Discovery of /api/v1/*.py Routers
# -------------------------------------------------------------
def discover_routers():
    import app.api.v1 as api_v1_pkg
    for _, module_name, is_pkg in pkgutil.iter_modules(api_v1_pkg.__path__):
        if not is_pkg and not module_name.startswith("__"):
            try:
                mod = importlib.import_module(f"app.api.v1.{module_name}")
                router = getattr(mod, "router", None)
                if router and isinstance(router, APIRouter):
                    # If router defines its own prefix, mount directly under v1_router
                    # Otherwise, mount under prefix '/<module_name>'
                    if router.prefix:
                        v1_router.include_router(router)
                        if router.prefix in ["/incidents", "/impact", "/disruptions"]:
                            app.include_router(router)
                    else:
                        v1_router.include_router(router, prefix=f"/{module_name}")
            except Exception as e:
                logger.error(f"Error loading router from app.api.v1.{module_name}: {e}")

discover_routers()
app.include_router(v1_router)
