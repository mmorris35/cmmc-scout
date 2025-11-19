"""Authentication module for CMMC Scout."""

from .auth0_client import get_auth0_config, verify_token
from .middleware import require_auth, require_role, get_current_user

__all__ = [
    "get_auth0_config",
    "verify_token",
    "require_auth",
    "require_role",
    "get_current_user",
]
