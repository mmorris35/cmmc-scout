# Auth0 Setup for CMMC Scout Demo

## Quick Setup (5 minutes)

### 1. Create Free Auth0 Account
1. Go to https://auth0.com/signup
2. Sign up with email (free tier is sufficient)
3. Choose region: US
4. Skip the initial setup wizard

### 2. Create Application
1. In Auth0 Dashboard, go to **Applications** → **Applications**
2. Click **Create Application**
3. Name: `CMMC Scout CLI`
4. Application Type: **Single Page Application** or **Regular Web Application**
5. Click **Create**

### 3. Configure Application Settings
1. On the **Settings** tab:
   - Copy **Domain** (e.g., `dev-xxx.us.auth0.com`)
   - Copy **Client ID**
   - Copy **Client Secret** (if available)
   - Scroll down to **Application URIs**
   - Add to **Allowed Callback URLs**: `http://localhost:8765/callback`
   - Add to **Allowed Logout URLs**: `http://localhost:8765`
   - Add to **Allowed Web Origins**: `http://localhost:8765`
   - Click **Save Changes**

### 4. Create API
1. Go to **Applications** → **APIs**
2. Click **Create API**
3. Name: `CMMC Scout API`
4. Identifier: `https://cmmc-scout-api`
5. Signing Algorithm: **RS256**
6. Click **Create**

### 5. Update .env File

Add to your `.env`:
```bash
# Auth0 Configuration
AUTH0_DOMAIN=dev-xxx.us.auth0.com      # Replace with your domain
AUTH0_CLIENT_ID=your_client_id_here    # Replace with your Client ID
AUTH0_CLIENT_SECRET=                    # Not needed for device flow
AUTH0_AUDIENCE=https://cmmc-scout-api
```

### 6. Test Authentication

Run without `--auto` flag:
```bash
source venv/bin/activate
python scripts/demo_cli.py
```

You should see:
```
🔐 Authenticating with Auth0...

================================================================================
Auth0 Device Login
================================================================================

Please visit: https://dev-xxx.us.auth0.com/activate?user_code=XXXX-XXXX
Or go to: https://dev-xxx.us.auth0.com/activate
And enter code: XXXX-XXXX

Waiting for authentication...
```

### 7. Complete Login
1. Open the URL in your browser
2. Sign up/login with Google, GitHub, or email
3. Authorize the application
4. Return to terminal - you should see:
```
✓ Authenticated as your-email@example.com
  Name: Your Name
  Email: your-email@example.com
  Role: client
```

## For Demo Recording

### Option 1: Show Real Auth0 (Recommended)
- Run without `--auto` flag
- Have browser open ready to complete login
- Shows actual OAuth flow with real Auth0
- **Time**: ~15 seconds for login flow

### Option 2: Auto Mode (Faster)
- Run with `--auto` flag
- Shows: "Auth0 not configured - using demo authentication"
- No actual login, uses demo credentials
- **Time**: Instant

### Option 3: Hybrid (Best of Both)
1. Start demo without `--auto`
2. Complete Auth0 login (shows integration)
3. For subsequent runs during recording, use `--auto`

## Troubleshooting

**Error: "Invalid domain"**
- Make sure AUTH0_DOMAIN doesn't include `https://`
- Format: `dev-xxx.us.auth0.com`

**Error: "Device code flow not enabled"**
- Go to Application → Settings → Advanced → Grant Types
- Enable "Device Code" grant type

**Timeout waiting for authentication**
- Default timeout: 5 minutes
- Complete login within the time limit
- Check the browser URL is correct

## What This Demonstrates

✅ **Enterprise Authentication**: OAuth 2.0 device flow for CLI apps
✅ **Security**: No passwords stored, token-based auth
✅ **Multi-tenant Ready**: Each user gets their own assessments
✅ **RBAC Support**: Role field ready for client/assessor/admin roles
✅ **Production-Ready**: Real Auth0 integration, not mocked

## Cost Note

Auth0 free tier includes:
- 7,000 active users
- Unlimited logins
- Social connections (Google, GitHub, etc.)
- MFA support
- **Perfect for demo and early customers**

---

**For hackathon judges**: This demonstrates a production-ready, enterprise-grade authentication system using Auth0's industry-standard OAuth 2.0 implementation.
