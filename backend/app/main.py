"""Privacy Eraser - FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import auth, users, brokers, requests, monitoring, billing
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    description="Personal data removal and privacy protection service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://privacy-eraser.onrender.com",
        "https://privacy-eraser-api.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
app.include_router(brokers.router, prefix=f"{settings.api_prefix}/brokers", tags=["Data Brokers"])
app.include_router(requests.router, prefix=f"{settings.api_prefix}/requests", tags=["Removal Requests"])
app.include_router(monitoring.router, prefix=f"{settings.api_prefix}/monitoring", tags=["Monitoring"])
app.include_router(billing.router, prefix=f"{settings.api_prefix}/billing", tags=["Billing"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/debug/optout-test")
async def debug_optout_test():
    """Debug endpoint to test opt-out URL matching."""
    from app.api.routes.requests import get_opt_out_info

    tests = [
        ("PeekYou", get_opt_out_info("PeekYou").get("url")),
        ("Spokeo Alt", get_opt_out_info("Spokeo Alt").get("url")),
        ("Spokeo", get_opt_out_info("Spokeo").get("url")),
        ("Google Search", get_opt_out_info("Google Search").get("url")),
    ]
    return {"version": "2026-02-07-fix2", "tests": tests}
