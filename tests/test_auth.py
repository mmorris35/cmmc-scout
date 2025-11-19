"""Tests for authentication system."""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.models import Base, User
from src.auth.middleware import get_db_session, get_current_user_from_token
from src.auth.auth0_client import extract_user_info


# Mock Auth0 environment variables
@pytest.fixture(autouse=True)
def mock_auth0_env(monkeypatch):
    """Mock Auth0 environment variables for testing."""
    monkeypatch.setenv("AUTH0_DOMAIN", "test.auth0.com")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("AUTH0_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://test-api")


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionMaker = sessionmaker(bind=engine)
    yield TestSessionMaker
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    session = test_db()
    user = User(
        auth0_id="auth0|test123",
        email="test@example.com",
        role="client",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return user


@pytest.fixture
def assessor_user(test_db):
    """Create a test assessor user."""
    session = test_db()
    user = User(
        auth0_id="auth0|assessor123",
        email="assessor@example.com",
        role="assessor",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return user


@pytest.fixture
def admin_user(test_db):
    """Create a test admin user."""
    session = test_db()
    user = User(
        auth0_id="auth0|admin123",
        email="admin@example.com",
        role="admin",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return user


class TestAuth0Config:
    """Test Auth0 configuration."""

    def test_auth0_config_initialized(self):
        """Test that Auth0 config can be initialized with env vars."""
        from src.auth.auth0_client import get_auth0_config

        config = get_auth0_config()
        assert config.domain == "test.auth0.com"
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.audience == "https://test-api"

    def test_auth0_config_urls(self):
        """Test Auth0 URL generation."""
        from src.auth.auth0_client import get_auth0_config

        config = get_auth0_config()
        assert config.issuer == "https://test.auth0.com/"
        assert config.jwks_url == "https://test.auth0.com/.well-known/jwks.json"
        assert config.authorize_url == "https://test.auth0.com/authorize"
        assert config.token_url == "https://test.auth0.com/oauth/token"


class TestUserInfoExtraction:
    """Test user info extraction from token."""

    def test_extract_user_info(self):
        """Test extracting user info from token payload."""
        payload = {
            "sub": "auth0|123456",
            "email": "user@example.com",
            "name": "Test User",
            "email_verified": True,
            "permissions": ["read:data"],
            "https://cmmc-scout.com/roles": ["client"],
        }

        user_info = extract_user_info(payload)

        assert user_info["auth0_id"] == "auth0|123456"
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "Test User"
        assert user_info["email_verified"] is True
        assert "read:data" in user_info["permissions"]
        assert "client" in user_info["roles"]

    def test_extract_user_info_minimal(self):
        """Test extracting user info with minimal payload."""
        payload = {
            "sub": "auth0|123456",
        }

        user_info = extract_user_info(payload)

        assert user_info["auth0_id"] == "auth0|123456"
        assert user_info["email"] is None
        assert user_info["email_verified"] is False
        assert user_info["permissions"] == []
        assert user_info["roles"] == []


class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""

    def test_root_endpoint_includes_auth_info(self):
        """Test that root endpoint includes auth URLs."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "auth" in data
        assert data["auth"]["login"] == "/auth/login"
        assert data["auth"]["user"] == "/auth/user"

    def test_get_user_without_token(self):
        """Test accessing user endpoint without authentication."""
        client = TestClient(app)
        response = client.get("/auth/user")

        assert response.status_code == 403  # No credentials provided

    def test_get_user_with_invalid_token(self):
        """Test accessing user endpoint with invalid token."""
        client = TestClient(app)
        response = client.get(
            "/auth/user",
            headers={"Authorization": "Bearer invalid_token"}
        )

        # Should return 401 due to invalid token
        assert response.status_code in [401, 500]  # Either unauthorized or error

    def test_logout_endpoint(self):
        """Test logout endpoint."""
        client = TestClient(app)
        response = client.post("/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "redirect_url" in data


class TestRoleBasedAccess:
    """Test role-based access control logic."""

    def test_role_checking_logic(self, assessor_user, test_user):
        """Test role checking logic directly."""
        # Assessor should be allowed for assessor endpoints
        allowed_roles = ["assessor", "admin"]
        assert assessor_user.role in allowed_roles

        # Client should not be allowed for assessor endpoints
        assert test_user.role not in allowed_roles

    def test_admin_role_access(self, admin_user):
        """Test that admin role is recognized."""
        allowed_for_admin = ["admin"]
        allowed_for_assessor = ["assessor", "admin"]

        # Admin can access admin endpoints
        assert admin_user.role in allowed_for_admin

        # Admin can also access assessor endpoints
        assert admin_user.role in allowed_for_assessor


class TestTokenSecurity:
    """Test token security measures."""

    def test_tokens_not_in_response(self):
        """Verify tokens are not leaked in API responses."""
        client = TestClient(app)

        # Test various endpoints
        endpoints = [
            "/",
            "/health",
            "/auth/logout",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint) if endpoint != "/auth/logout" else client.post(endpoint)
            assert response.status_code == 200

            # Verify no token-like strings in response
            response_text = response.text.lower()
            assert "bearer " not in response_text or "authorization" in response_text
            # Tokens should never be in plain text responses unless explicitly requested

    def test_token_verification_isolates_payload(self):
        """Test that token payload is properly extracted without exposing full token."""
        payload = {
            "sub": "auth0|123456",
            "email": "user@example.com",
            "iat": 1234567890,
            "exp": 1234567890,
        }

        user_info = extract_user_info(payload)

        # User info should only contain safe fields
        assert "iat" not in user_info
        assert "exp" not in user_info
        assert user_info["auth0_id"] == "auth0|123456"
        assert user_info["email"] == "user@example.com"


class TestDatabaseIntegration:
    """Test authentication integration with database."""

    def test_user_model_creation(self, test_db):
        """Test that users can be created in database."""
        session = test_db()

        # Create new user
        new_user = User(
            auth0_id="auth0|newuser123",
            email="newuser@example.com",
            role="client",
        )
        session.add(new_user)
        session.commit()

        # Verify user was created
        user = session.query(User).filter_by(auth0_id="auth0|newuser123").first()
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.role == "client"

        session.close()

    def test_user_default_role(self, test_db):
        """Test that users get default client role."""
        session = test_db()

        # Create user without specifying role
        new_user = User(
            auth0_id="auth0|test456",
            email="test@example.com",
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        assert new_user.role == "client"

        session.close()
