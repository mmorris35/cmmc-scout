"""FastAPI application for CMMC Scout."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="CMMC Scout API",
    description="AI-powered CMMC Level 2 compliance assessment agent",
    version="0.1.0",
)

# Import and include routers
try:
    from src.auth.routes import router as auth_router
    app.include_router(auth_router)
except Exception as e:
    # Auth0 not configured - continue without auth routes
    print(f"Warning: Auth routes not loaded ({e})")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse: Current application health status
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        dict: Welcome message
    """
    return {
        "message": "CMMC Scout API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "auth": {
            "login": "/auth/login",
            "user": "/auth/user",
            "verify": "/auth/verify",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
