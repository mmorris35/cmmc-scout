"""Interactive CLI demo for CMMC Scout.

This script demonstrates the assessment workflow with a simple
command-line interface for hackathon demonstrations.
"""

import sys
import os
from uuid import uuid4
from datetime import datetime
import time

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
from src.agents.assessment_agent import create_assessment_agent
from src.services.report_service import generate_gap_report, export_report_markdown
from sqlalchemy.orm import sessionmaker


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


def run_demo():
    """Run interactive demo."""
    print_header("CMMC Scout - AI-Powered Compliance Assessment")

    print(f"{Colors.CYAN}Welcome to CMMC Scout!")
    print("This demo shows an AI-powered CMMC Level 2 assessment for the Access Control domain.")
    print(f"Press ENTER to continue...{Colors.END}")
    input()

    # Setup database
    print_status("🔧", "Setting up database...")
    engine = get_db_engine(database_url="sqlite:///demo.db")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Create demo user
    user = User(
        id=uuid4(),
        auth0_id="demo|user",
        email="demo@example.com",
        role="client",
    )
    session.add(user)

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
        agent = create_assessment_agent(control_data, enable_comet=False)  # Disable Comet for demo
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
        time.sleep(1)  # Simulate processing

        result = agent.classify_response(user_response)

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

        # Display classification
        print_classification(result["classification"], result.get("explanation", ""))

        if result.get("remediation"):
            print(f"{Colors.YELLOW}📝 Remediation Needed:{Colors.END}")
            print(f"{Colors.YELLOW}{result['remediation']}{Colors.END}\n")

        if i < len(demo_controls) - 1:
            print(f"{Colors.CYAN}Press ENTER for next control...{Colors.END}")
            input()

    # Complete assessment
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

    session.close()


def main():
    """Main entry point."""
    try:
        run_demo()
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
