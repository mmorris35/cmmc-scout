# Auth0 OAuth 2.0 Integration - Authorization Code Flow
# From scripts/demo_cli.py:131-274

def authenticate_with_auth0(auto_mode=False):
    """Authenticate user with Auth0 browser-based OAuth flow."""

    # Load Auth0 configuration from environment
    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    auth0_audience = os.getenv("AUTH0_AUDIENCE")

    # Generate CSRF protection state token
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_url = (
        f"https://{auth0_domain}/authorize?"
        f"response_type=code&"
        f"client_id={auth0_client_id}&"
        f"redirect_uri=http://localhost:8765/callback&"
        f"scope=openid profile email&"
        f"audience={auth0_audience}&"
        f"state={state}"
    )

    # Open browser for user authentication
    webbrowser.open(auth_url)

    # Start local HTTP server to receive callback
    with HTTPServer(("", 8765), CallbackHandler) as server:
        server.handle_request()

        # Exchange authorization code for access token
        token_response = requests.post(
            f"https://{auth0_domain}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": auth0_client_id,
                "client_secret": auth0_client_secret,
                "code": received_code,
                "redirect_uri": "http://localhost:8765/callback"
            }
        )

        access_token = token_response.json()["access_token"]

        # Get user profile from Auth0
        user_info = requests.get(
            f"https://{auth0_domain}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        # Store user in database for multi-tenant access
        user = create_or_update_user(
            auth0_id=user_info["sub"],
            email=user_info.get("email"),
            name=user_info.get("name"),
            role="client"  # Default role for new users
        )

        return user_info, access_token
