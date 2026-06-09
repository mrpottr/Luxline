"""Application factory and router wiring for the Luxline API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.bootstrap import ensure_default_admin
from backend.app.db.schema import ensure_schema_compatibility
from backend.app.db.session import SessionLocal, engine
from backend.app.routers import admin, agencies, auth, health, leads, listings, localization, monetization, search, users

# Prometheus metrics
REQUEST_COUNT = Counter(
    "luxline_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)
REQUEST_DURATION = Histogram(
    "luxline_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)
REQUEST_SIZE = Histogram(
    "luxline_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"]
)
RESPONSE_SIZE = Histogram(
    "luxline_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"]
)
ACTIVE_REQUESTS = Gauge(
    "luxline_active_requests",
    "Current number of active requests",
    ["method", "endpoint"]
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance.

    The app configures CORS, ensures tables exist, and registers all versioned routers.
    """
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    origins = [origin.strip() for origin in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        """Middleware to collect Prometheus metrics."""
        method = request.method
        endpoint = request.url.path
        
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        request_size = len(await request.body())
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            REQUEST_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
            response_size = int(response.headers.get("content-length", 0) or 0)
            RESPONSE_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
            
            return response
        finally:
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()

    ensure_schema_compatibility(engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_default_admin(db)

    app.include_router(health.router)
    
    @app.get("/metrics", tags=["monitoring"])
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(agencies.router, prefix=api_prefix)
    app.include_router(listings.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(leads.router, prefix=api_prefix)
    app.include_router(monetization.router, prefix=api_prefix)
    app.include_router(localization.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)

    return app


app = create_app()
