"""
FastAPI Application Entry Point.

This file instantiates the FastAPI application, registers global middlewares (CORS),
mounts API version routers, and defines root-level informational endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

# Initialize FastAPI application with rich OpenAPI metadata for Swagger UI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Backend REST API for NGO Disaster Relief Management System.\n\n"
        "Features:\n"
        "- Role-based Access Control (Admin, NGO Staff, Volunteer, Donor)\n"
        "- Disaster & Event Lifecycle Management\n"
        "- Volunteer Task Assignment & Tracking\n"
        "- Donation Management & Relief Inventory\n"
        "- Beneficiary Registration & Aid Distribution\n"
        "- Real-time Disaster Relief Reports & Metrics"
    ),
    version=settings.PROJECT_VERSION,
    docs_url="/docs",      # Interactive Swagger UI
    redoc_url="/redoc",    # Alternative ReDoc documentation
    openapi_url="/openapi.json",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows frontend clients (React/Vue/Mobile) to consume this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the centralized API v1 router under the configured prefix (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/",
    tags=["Root"],
    summary="Root Welcome Endpoint",
    description="Welcome message and pointers to interactive API documentation.",
)
def read_root():
    """
    Root endpoint to verify that the server is online.
    Directs developers and evaluators to the interactive documentation.
    """
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API!",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": f"{settings.API_V1_STR}/health",
    }
