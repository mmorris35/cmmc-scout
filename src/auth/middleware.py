"""FastAPI middleware for authentication and authorization."""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .auth0_client import verify_token, extract_user_info
from src.models import User, get_session_maker


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Extract and verify user from Bearer token.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        User information dictionary

    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials

    try:
        # Verify token with Auth0
        payload = await verify_token(token)

        # Extract user info
        user_info = extract_user_info(payload)

        if not user_info.get("auth0_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        return user_info

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        )


def get_db_session():
    """
    Get database session dependency.

    Yields:
        SQLAlchemy session
    """
    SessionMaker = get_session_maker()
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


async def get_current_user(
    user_info: dict = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session),
) -> User:
    """
    Get current user from database, creating if doesn't exist.

    Args:
        user_info: User info from verified token
        db: Database session

    Returns:
        User model instance

    Raises:
        HTTPException: If user cannot be retrieved or created
    """
    auth0_id = user_info["auth0_id"]

    # Try to get existing user
    user = db.query(User).filter_by(auth0_id=auth0_id).first()

    if user is None:
        # Create new user on first login
        user = User(
            auth0_id=auth0_id,
            email=user_info.get("email", ""),
            role="client",  # Default role
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require authentication.

    Args:
        current_user: Current authenticated user

    Returns:
        User instance

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(require_auth)):
            return {"user_id": user.id}
    """
    return current_user


def require_role(allowed_roles: List[str]):
    """
    Dependency factory to require specific roles.

    Args:
        allowed_roles: List of allowed role names

    Returns:
        Dependency function

    Usage:
        @app.get("/admin")
        async def admin_route(user: User = Depends(require_role(["admin"]))):
            return {"message": "Admin access granted"}
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# Convenience role dependencies
def require_assessor(current_user: User = Depends(require_role(["assessor", "admin"]))) -> User:
    """Require assessor or admin role."""
    return current_user


def require_admin(current_user: User = Depends(require_role(["admin"]))) -> User:
    """Require admin role."""
    return current_user


# Optional authentication (user may or may not be logged in)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User instance if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = await verify_token(token)
        user_info = extract_user_info(payload)

        auth0_id = user_info["auth0_id"]
        user = db.query(User).filter_by(auth0_id=auth0_id).first()

        return user
    except Exception:
        # Invalid token, but that's okay for optional auth
        return None
