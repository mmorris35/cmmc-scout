"""Authentication routes for CMMC Scout."""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from .auth0_client import get_auth0_config, get_oauth_client
from .middleware import get_current_user, require_auth, require_role
from src.models import User


router = APIRouter(prefix="/auth", tags=["authentication"])


class UserResponse(BaseModel):
    """User profile response."""

    id: str
    auth0_id: str
    email: str
    role: str
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None


@router.get("/login")
async def login(request: Request):
    """
    Initiate Auth0 login flow.

    Redirects user to Auth0 login page.
    """
    try:
        config = get_auth0_config()
        oauth = get_oauth_client()

        # Redirect to Auth0 for authentication
        redirect_uri = config.callback_url
        return await oauth.auth0.authorize_redirect(request, redirect_uri)

    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Auth0 configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@router.get("/callback")
async def callback(request: Request):
    """
    Handle Auth0 callback after login.

    Exchanges authorization code for access token.
    """
    try:
        oauth = get_oauth_client()

        # Get token from Auth0
        token = await oauth.auth0.authorize_access_token(request)

        # Extract user info from token
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(status_code=400, detail="No user info in token")

        # For demo purposes, return token
        # In production, you'd typically set a session cookie here
        return JSONResponse({
            "message": "Authentication successful",
            "token": token.get("access_token"),
            "user": {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")


@router.get("/user", response_model=UserResponse)
async def get_user_profile(user: User = Depends(require_auth)):
    """
    Get current user profile.

    Requires authentication.
    """
    return UserResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


@router.post("/logout")
async def logout():
    """
    Logout user.

    In a real implementation, this would invalidate the session/token.
    For stateless JWT, client should discard the token.
    """
    return {
        "message": "Logged out successfully. Please discard your access token.",
        "redirect_url": f"https://{get_auth0_config().domain}/v2/logout"
    }


@router.get("/verify")
async def verify_token_route(user: User = Depends(require_auth)):
    """
    Verify that a token is valid.

    Returns user info if token is valid.
    """
    return {
        "valid": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    }


# Role-based access examples
@router.get("/admin/test")
async def admin_test(user: User = Depends(require_role(["admin"]))):
    """
    Test endpoint requiring admin role.

    Only accessible by users with 'admin' role.
    """
    return {
        "message": "Admin access granted",
        "user_id": str(user.id),
        "role": user.role,
    }


@router.get("/assessor/test")
async def assessor_test(user: User = Depends(require_role(["assessor", "admin"]))):
    """
    Test endpoint requiring assessor or admin role.

    Accessible by users with 'assessor' or 'admin' role.
    """
    return {
        "message": "Assessor access granted",
        "user_id": str(user.id),
        "role": user.role,
    }
