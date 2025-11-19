"""API routes for CMMC Scout."""

from .assessment_routes import router as assessment_router

__all__ = ["assessment_router"]
