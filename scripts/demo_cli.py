"""Interactive CLI demo for CMMC Scout.

This script demonstrates the assessment workflow with a simple
command-line interface for hackathon demonstrations.
"""

import sys
import os
from uuid import uuid4
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.database import (
    Base,
    User,
    Assessment,
    ControlResponse,
    get_db_engine,
)
from src.services.control_service import get_control_service
from src.services.report_service import generate_gap_report, export_report_markdown
from src.agents.assessment_agent import create_assessment_agent
from src.actors.session_actor import SessionActor
from src.actors.domain_actor import DomainActor
from src.actors.scoring_actor import ScoringActor
from sqlalchemy.orm import sessionmaker
import httpx
import json as json_module
import webbrowser
import secrets
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}\n")


def print_status(emoji, text, color=Colors.CYAN):
    """Print status message."""
    print(f"{color}{emoji} {text}{Colors.END}")


def print_question(question):
    """Print assessment question."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}QUESTION:{Colors.END}")
    print(f"{Colors.BLUE}{question}{Colors.END}\n")


def print_classification(classification, explanation):
    """Print classification result."""
    emoji_map = {
        "compliant": ("✓", Colors.GREEN),
        "partial": ("⚠", Colors.YELLOW),
        "non_compliant": ("✗", Colors.RED),
    }

    emoji, color = emoji_map.get(classification, ("?", Colors.CYAN))

    print(f"\n{color}{Colors.BOLD}{emoji} CLASSIFICATION: {classification.upper()}{Colors.END}")
    print(f"{color}{explanation}{Colors.END}\n")


# Global variable to store auth callback data
_auth_callback_data = {}


class Auth0CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Auth0 callback."""

    def do_GET(self):
        """Handle GET request with authorization code."""
        global _auth_callback_data

        # Parse query parameters
        query_string = self.path.split('?', 1)[1] if '?' in self.path else ''
        params = parse_qs(query_string)

        if 'code' in params:
            _auth_callback_data['code'] = params['code'][0]
            _auth_callback_data['state'] = params.get('state', [''])[0]

            # Send success page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <head><title>CMMC Scout - Login Successful</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #28a745;">✓ Authentication Successful!</h1>
                <p>You can now close this window and return to the terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif 'error' in params:
            _auth_callback_data['error'] = params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = f"""
            <html>
            <head><title>CMMC Scout - Login Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #dc3545;">✗ Authentication Failed</h1>
                <p>Error: {params['error'][0]}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress server logs."""
        pass


def authenticate_with_auth0(auto_mode=False):
    """
    Authenticate user with Auth0 using authorization code flow.

    Args:
        auto_mode: If True, skip actual Auth0 and use demo credentials

    Returns:
        Tuple of (user_info dict, access_token) or (None, None) if failed
    """
    global _auth_callback_data

    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET", "")
    auth0_audience = os.getenv("AUTH0_AUDIENCE", "https://cmmc-scout-api")

    # Skip Auth0 if not configured or in auto mode
    if not auth0_domain or not auth0_client_id or auth0_client_id == "your_client_id_here" or auto_mode:
        print_status("🔐", "Auth0 not configured - using demo authentication", Colors.YELLOW)
        return {
            "auth0_id": "demo|user",
            "email": "demo@example.com",
            "name": "Demo User",
            "role": "client"
        }, None

    print_status("🔐", "Authenticating with Auth0...")

    try:
        # Start local callback server
        callback_port = 8765
        callback_url = f"http://localhost:{callback_port}/callback"

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": auth0_client_id,
            "redirect_uri": callback_url,
            "scope": "openid profile email",
            "state": state,
            "audience": auth0_audience,
        }

        auth_url = f"https://{auth0_domain}/authorize?{urlencode(auth_params)}"

        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}Auth0 Browser Login{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
        print(f"{Colors.YELLOW}Opening browser for authentication...{Colors.END}")
        print(f"{Colors.CYAN}If browser doesn't open, visit: {auth_url[:60]}...{Colors.END}\n")

        # Start callback server in background
        _auth_callback_data = {}
        server = HTTPServer(('localhost', callback_port), Auth0CallbackHandler)

        def run_server():
            server.handle_request()  # Handle one request then stop

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Open browser
        webbrowser.open(auth_url)

        print(f"{Colors.CYAN}Waiting for login to complete...{Colors.END}\n")

        # Wait for callback (max 2 minutes)
        import time as time_module
        timeout = 120
        start = time_module.time()

        while time_module.time() - start < timeout:
            if _auth_callback_data:
                break
            time_module.sleep(0.5)

        server.server_close()

        if 'error' in _auth_callback_data:
            print_status("✗", f"Authentication failed: {_auth_callback_data['error']}", Colors.RED)
            return None, None

        if 'code' not in _auth_callback_data:
            print_status("✗", "Authentication timeout", Colors.RED)
            return None, None

        # Verify state
        if _auth_callback_data.get('state') != state:
            print_status("✗", "Authentication failed: invalid state", Colors.RED)
            return None, None

        # Exchange code for token
        with httpx.Client() as client:
            token_response = client.post(
                f"https://{auth0_domain}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": auth0_client_id,
                    "client_secret": auth0_client_secret,
                    "code": _auth_callback_data['code'],
                    "redirect_uri": callback_url,
                }
            )

            if token_response.status_code != 200:
                print_status("✗", f"Token exchange failed: {token_response.text}", Colors.RED)
                return None, None

            token_data = token_response.json()
            access_token = token_data["access_token"]

            # Get user info
            userinfo_response = client.get(
                f"https://{auth0_domain}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()

            print_status("✓", f"Authenticated as {user_info.get('email', user_info.get('sub'))}", Colors.GREEN)
            print(f"  Name: {user_info.get('name', 'N/A')}")
            print(f"  Email: {user_info.get('email', 'N/A')}")
            print(f"  Role: client\n")

            return {
                "auth0_id": user_info["sub"],
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "role": "client"
            }, access_token

    except Exception as e:
        print_status("⚠", f"Auth0 error: {e}", Colors.YELLOW)
        print_status("🔐", "Falling back to demo authentication", Colors.YELLOW)
        return {
            "auth0_id": "demo|user",
            "email": "demo@example.com",
            "name": "Demo User",
            "role": "client"
        }, None


def run_demo(auto_mode=False):
    """Run interactive demo.

    Args:
        auto_mode: If True, automatically advance without waiting for user input
    """
    print_header("CMMC Scout - AI-Powered Compliance Assessment")

    print(f"{Colors.CYAN}Welcome to CMMC Scout!")
    print("This demo shows an AI-powered CMMC Level 2 assessment for the Access Control domain.")
    if not auto_mode:
        print(f"Press ENTER to continue...{Colors.END}")
        input()
    else:
        print(f"[Auto-mode enabled]{Colors.END}")
        time.sleep(1)

    # Authenticate with Auth0
    user_info, access_token = authenticate_with_auth0(auto_mode=auto_mode)
    if not user_info:
        print(f"\n{Colors.RED}Authentication failed. Exiting.{Colors.END}\n")
        return

    # Setup database
    print_status("🔧", "Setting up database...")
    engine = get_db_engine(database_url="sqlite:///demo.db")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Create or get user from Auth0 info
    user = session.query(User).filter_by(auth0_id=user_info["auth0_id"]).first()
    if not user:
        user = User(
            id=uuid4(),
            auth0_id=user_info["auth0_id"],
            email=user_info.get("email", "unknown@example.com"),
            role=user_info.get("role", "client"),
        )
        session.add(user)
        session.commit()
        print_status("✓", "User account created", Colors.GREEN)
    else:
        print_status("✓", "Existing user found", Colors.GREEN)

    # Create assessment
    assessment = Assessment(
        id=uuid4(),
        user_id=user.id,
        domain="Access Control",
        status="in_progress",
    )
    session.add(assessment)
    session.commit()

    print_status("✓", "Assessment created!", Colors.GREEN)
    print(f"  Assessment ID: {assessment.id}")
    print(f"  Domain: {assessment.domain}\n")

    # Initialize Akka actors for stateful session management
    print_status("🎭", "Starting Akka actor system...", Colors.CYAN)
    session_actor = SessionActor.start(user_id=user.auth0_id, assessment_id=assessment.id).proxy()
    domain_actor = DomainActor.start(
        user_id=user.auth0_id,
        assessment_id=assessment.id,
        domain="Access Control"
    ).proxy()
    scoring_actor = ScoringActor.start().proxy()
    print_status("✓", "Actors initialized (SessionActor, DomainActor, ScoringActor)", Colors.GREEN)

    # Start assessment through actor system
    start_result = session_actor.on_receive({
        "type": "START_ASSESSMENT",
        "domain": "Access Control"
    }).get()

    if not start_result.get("success"):
        print_status("✗", f"Actor failed to start assessment: {start_result.get('error')}", Colors.RED)
        return

    # Get controls
    control_service = get_control_service()
    controls = control_service.get_controls_by_domain("Access Control")

    print_status("📋", f"Loaded {len(controls)} controls for assessment")

    # Demo with first 4 controls (shortened for demo)
    demo_controls = controls[:4]

    # Predefined responses for demo
    demo_responses = [
        {
            "response": "We have a documented access control policy approved by management. All access requests go through ServiceNow with approval workflows and audit logging.",
            "expected": "compliant"
        },
        {
            "response": "We use role-based access control in Active Directory. Users are assigned to security groups based on job function.",
            "expected": "compliant"
        },
        {
            "response": "We have some separation of duties for financial transactions, but IT administrators have broad access to most systems.",
            "expected": "partial"
        },
        {
            "response": "We don't have automatic session timeout configured. Users can stay logged in indefinitely.",
            "expected": "non_compliant"
        },
    ]

    print(f"\n{Colors.CYAN}Starting interactive assessment...{Colors.END}\n")
    time.sleep(1)

    responses = []

    for i, control in enumerate(demo_controls):
        print_header(f"Control {i+1} of {len(demo_controls)}")

        print(f"{Colors.BOLD}Control: {control.control_id} - {control.title}{Colors.END}")
        print(f"Requirement: {control.requirement[:150]}...")

        # Create agent
        control_data = {
            "control_id": control.control_id,
            "domain": control.domain,
            "title": control.title,
            "requirement": control.requirement,
            "assessment_objective": control.assessment_objective,
            "discussion": control.discussion,
        }

        print_status("🤖", "Generating question with AI agent...")

        # Create assessment agent for this control (with Comet tracking enabled)
        agent = create_assessment_agent(control_data, enable_comet=True)

        # Generate question using real LLM
        question = agent.generate_question()
        print_question(question)

        # Get user response (or use predefined for automated demo)
        if i < len(demo_responses):
            print(f"{Colors.YELLOW}[Demo mode - using predefined response]{Colors.END}")
            user_response = demo_responses[i]["response"]
            print(f"{Colors.CYAN}Response: {user_response}{Colors.END}")
        else:
            user_response = input(f"{Colors.CYAN}Your response: {Colors.END}")

        # Classify response
        print_status("🔍", "Analyzing response with AI agent...")

        # Use real LLM to classify the response
        result = agent.classify_response(user_response)

        # Process through domain actor (handles events & gap identification)
        domain_actor.on_receive({
            "type": "EVALUATE_CONTROL",
            "control_id": control.control_id,
            "control_title": control.title,
            "user_response": user_response,
            "classification": result["classification"],
            "agent_notes": result.get("explanation", ""),
            "evidence_provided": bool(user_response and len(user_response) > 50)
        }).get()

        # Save to database
        control_response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=control.control_id,
            control_title=control.title,
            user_response=user_response,
            classification=result["classification"],
            agent_notes=result.get("explanation"),
            remediation_notes=result.get("remediation"),
        )
        session.add(control_response)
        session.commit()
        responses.append(control_response)

        # Submit response to session actor for state management
        session_actor.on_receive({
            "type": "SUBMIT_RESPONSE",
            "control_id": control.control_id,
            "control_title": control.title,
            "classification": result["classification"],
            "user_response": user_response,
            "agent_notes": result.get("explanation", "")
        }).get()

        # Display classification
        print_classification(result["classification"], result.get("explanation", ""))

        if result.get("remediation"):
            print(f"{Colors.YELLOW}📝 Remediation Needed:{Colors.END}")
            print(f"{Colors.YELLOW}{result['remediation']}{Colors.END}\n")

        if i < len(demo_controls) - 1:
            if not auto_mode:
                print(f"{Colors.CYAN}Press ENTER for next control...{Colors.END}")
                input()
            else:
                time.sleep(1)

    # Calculate score using scoring actor
    print_status("🎯", "Calculating compliance score with ScoringActor...", Colors.CYAN)
    response_data = [
        {
            "control_id": r.control_id,
            "control_title": r.control_title,
            "classification": r.classification,
            "agent_notes": r.agent_notes
        }
        for r in responses
    ]
    scoring_result = scoring_actor.on_receive({
        "type": "CALCULATE_SCORE",
        "responses": response_data
    }).get()

    # Complete assessment through session actor
    session_actor.on_receive({
        "type": "COMPLETE_ASSESSMENT",
        "scoring_results": scoring_result
    }).get()

    # Complete assessment in database
    assessment.status = "completed"
    assessment.completed_at = datetime.utcnow()
    session.commit()

    print_header("Assessment Complete!")

    # Generate report
    print_status("📊", "Generating gap report...")
    time.sleep(1)

    report = generate_gap_report(assessment.id, session)

    # Display summary
    print(f"\n{Colors.BOLD}COMPLIANCE SCORE:{Colors.END}")

    traffic_light_colors = {
        "green": Colors.GREEN,
        "yellow": Colors.YELLOW,
        "red": Colors.RED,
    }

    color = traffic_light_colors.get(report.scoring.traffic_light, Colors.CYAN)

    print(f"{color}{Colors.BOLD}{report.scoring.compliance_percentage:.1f}% - {report.scoring.traffic_light.upper()}{Colors.END}\n")

    print(f"{Colors.BOLD}Results:{Colors.END}")
    print(f"  ✓ Compliant: {report.scoring.compliant_count}")
    print(f"  ⚠ Partial: {report.scoring.partial_count}")
    print(f"  ✗ Non-Compliant: {report.scoring.non_compliant_count}")

    if report.gaps:
        print(f"\n{Colors.BOLD}Identified Gaps:{Colors.END}")
        for gap in report.gaps[:3]:  # Show top 3
            severity_color = Colors.RED if gap.severity == "high" else Colors.YELLOW
            print(f"{severity_color}  [{gap.priority}/10] {gap.control_id}: {gap.gap_description[:100]}...{Colors.END}")

    # Save markdown report
    markdown_report = export_report_markdown(report)
    report_file = "demo_report.md"
    with open(report_file, "w") as f:
        f.write(markdown_report)

    print(f"\n{Colors.GREEN}✓ Full report saved to: {report_file}{Colors.END}")

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Demo complete! Thank you for trying CMMC Scout.{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")

    # Stop actors
    print_status("🎭", "Stopping Akka actors...", Colors.CYAN)
    session_actor.stop()
    domain_actor.stop()
    scoring_actor.stop()
    print_status("✓", "Actors stopped gracefully", Colors.GREEN)

    session.close()


def main():
    """Main entry point."""
    # Check for auto mode flag
    auto_mode = "--auto" in sys.argv or len(sys.argv) > 1 and sys.argv[1] == "auto"

    try:
        run_demo(auto_mode=auto_mode)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted. Exiting...{Colors.END}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
