"""Auth0 OAuth client configuration and token verification."""

import os
from typing import Dict, Optional
from jose import jwt, JWTError
from authlib.integrations.starlette_client import OAuth
import httpx


class Auth0Config:
    """Auth0 configuration."""

    def __init__(self):
        """Initialize Auth0 configuration from environment variables."""
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.client_id = os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET")
        self.audience = os.getenv("AUTH0_AUDIENCE")
        self.callback_url = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8000/auth/callback")

        # Validate required configuration
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError(
                "Auth0 configuration incomplete. Required: AUTH0_DOMAIN, "
                "AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET"
            )

    @property
    def issuer(self) -> str:
        """Get Auth0 issuer URL."""
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        """Get JWKS URL for token verification."""
        return f"https://{self.domain}/.well-known/jwks.json"

    @property
    def authorize_url(self) -> str:
        """Get Auth0 authorization URL."""
        return f"https://{self.domain}/authorize"

    @property
    def token_url(self) -> str:
        """Get Auth0 token URL."""
        return f"https://{self.domain}/oauth/token"

    @property
    def userinfo_url(self) -> str:
        """Get Auth0 userinfo URL."""
        return f"https://{self.domain}/userinfo"


# Global Auth0 config instance
_auth0_config: Optional[Auth0Config] = None


def get_auth0_config() -> Auth0Config:
    """
    Get or create Auth0 configuration instance.

    Returns:
        Auth0Config instance

    Raises:
        ValueError: If Auth0 configuration is incomplete
    """
    global _auth0_config

    if _auth0_config is None:
        _auth0_config = Auth0Config()

    return _auth0_config


# JWKS cache for token verification
_jwks_cache: Optional[Dict] = None


async def get_jwks() -> Dict:
    """
    Get JWKS (JSON Web Key Set) from Auth0.

    Uses caching to avoid repeated requests.

    Returns:
        JWKS dictionary
    """
    global _jwks_cache

    if _jwks_cache is None:
        config = get_auth0_config()
        async with httpx.AsyncClient() as client:
            response = await client.get(config.jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()

    return _jwks_cache


async def verify_token(token: str) -> Dict:
    """
    Verify and decode Auth0 JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload with user information

    Raises:
        JWTError: If token is invalid or expired
        ValueError: If token validation fails
    """
    config = get_auth0_config()

    try:
        # Get JWKS for signature verification
        jwks = await get_jwks()

        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        key_id = unverified_header.get("kid")

        # Find the signing key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == key_id:
                rsa_key = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e"),
                }
                break

        if rsa_key is None:
            raise ValueError("Unable to find appropriate signing key")

        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=config.audience,
            issuer=config.issuer,
        )

        return payload

    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def extract_user_info(token_payload: Dict) -> Dict:
    """
    Extract user information from verified token payload.

    Args:
        token_payload: Decoded JWT payload

    Returns:
        Dictionary with user information
    """
    # Auth0 tokens contain user info in different fields depending on configuration
    # Standard claims: sub (subject/user ID), email, name, etc.

    user_info = {
        "auth0_id": token_payload.get("sub"),  # Auth0 user ID
        "email": token_payload.get("email"),
        "name": token_payload.get("name"),
        "email_verified": token_payload.get("email_verified", False),
        "permissions": token_payload.get("permissions", []),
        "roles": token_payload.get("https://cmmc-scout.com/roles", []),  # Custom claim
    }

    return user_info


def get_oauth_client() -> OAuth:
    """
    Create and configure OAuth client for Auth0.

    Returns:
        Configured OAuth instance
    """
    config = get_auth0_config()

    oauth = OAuth()
    oauth.register(
        name="auth0",
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=f"https://{config.domain}/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid profile email",
        },
    )

    return oauth
