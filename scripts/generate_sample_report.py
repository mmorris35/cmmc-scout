"""Generate a sample CMMC assessment report for demonstration.

This script creates a sample assessment with responses and generates
a comprehensive gap report in both JSON and Markdown formats.
"""

import sys
import os
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.database import (
    Base,
    User,
    Assessment,
    ControlResponse,
    get_db_engine,
)
from src.services.report_service import (
    generate_gap_report,
    export_report_markdown,
    export_report_json,
)
from sqlalchemy.orm import sessionmaker


def create_sample_assessment():
    """Create a sample assessment with realistic responses."""
    # Create in-memory database
    engine = get_db_engine(database_url="sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Create user
    user = User(
        id=uuid4(),
        auth0_id="demo|user123",
        email="demo@example.com",
        role="client",
    )
    session.add(user)

    # Create assessment
    assessment = Assessment(
        id=uuid4(),
        user_id=user.id,
        domain="Access Control",
        status="completed",
        completed_at=datetime.utcnow(),
    )
    session.add(assessment)
    session.commit()

    # Add sample responses (mix of compliant, partial, non-compliant)
    sample_responses = [
        # Compliant controls
        {
            "control_id": "AC.L2-3.1.1",
            "control_title": "Authorized Access Control",
            "user_response": "We have a documented access control policy approved by management. All access requests go through our ServiceNow ticketing system which logs approvals with timestamps. We conduct quarterly access reviews.",
            "classification": "compliant",
            "agent_notes": "Excellent implementation with documented policy, automated tracking, and regular reviews. Meets all CMMC Level 2 requirements.",
            "remediation_notes": None,
        },
        {
            "control_id": "AC.L2-3.1.2",
            "control_title": "Transaction & Function Control",
            "user_response": "We use role-based access control (RBAC) in Active Directory. Users are assigned to security groups based on job function. Privileged access requires manager approval.",
            "classification": "compliant",
            "agent_notes": "Strong RBAC implementation with appropriate approval workflow for privileged access.",
            "remediation_notes": None,
        },
        {
            "control_id": "AC.L2-3.1.3",
            "control_title": "External Connections",
            "user_response": "We have a firewall with strict allow-list rules. VPN access requires multi-factor authentication. All external connections are logged.",
            "classification": "compliant",
            "agent_notes": "Comprehensive external access controls with MFA and logging.",
            "remediation_notes": None,
        },

        # Partially compliant controls
        {
            "control_id": "AC.L2-3.1.5",
            "control_title": "Separation of Duties",
            "user_response": "We have some separation of duties for financial transactions, but IT administrators have broad access to systems.",
            "classification": "partial",
            "agent_notes": "Partial implementation - financial controls exist but IT access needs refinement.",
            "remediation_notes": "Implement role separation for IT administrators\nDefine and enforce least privilege access model\nConduct access review to identify excessive privileges",
        },
        {
            "control_id": "AC.L2-3.1.6",
            "control_title": "Least Privilege",
            "user_response": "We try to limit access but haven't done a comprehensive review. Some users probably have more access than they need.",
            "classification": "partial",
            "agent_notes": "Awareness of least privilege principle but lacking systematic implementation.",
            "remediation_notes": "Conduct comprehensive access review\nDocument required access for each role\nRemove unnecessary permissions\nImplement quarterly access recertification",
        },
        {
            "control_id": "AC.L2-3.1.12",
            "control_title": "Session Lock",
            "user_response": "Most workstations have screen savers that lock after 15 minutes. We haven't verified all systems are configured correctly.",
            "classification": "partial",
            "agent_notes": "Basic screen lock in place but lacks enforcement and verification.",
            "remediation_notes": "Implement Group Policy to enforce screen lock (10-minute timeout)\nVerify configuration on all systems\nMonitor compliance through endpoint management",
        },

        # Non-compliant controls
        {
            "control_id": "AC.L2-3.1.13",
            "control_title": "Session Termination",
            "user_response": "We don't have automatic session termination. Users can stay logged in indefinitely.",
            "classification": "non_compliant",
            "agent_notes": "Critical gap - no session timeout controls implemented.",
            "remediation_notes": "Configure automatic session termination (30-minute idle timeout)\nImplement application-level session management\nTest across all critical systems\nDocument and communicate policy to users",
        },
        {
            "control_id": "AC.L2-3.1.14",
            "control_title": "Permitted Actions without Identification",
            "user_response": "We haven't specifically reviewed what functions are available without authentication.",
            "classification": "non_compliant",
            "agent_notes": "No documented analysis of unauthenticated access. Potential security gap.",
            "remediation_notes": "Conduct security assessment of all systems\nIdentify and document functions available without authentication\nMinimize unauthenticated functionality\nImplement technical controls to prevent unauthorized access",
        },
    ]

    for resp_data in sample_responses:
        response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=resp_data["control_id"],
            control_title=resp_data["control_title"],
            user_response=resp_data["user_response"],
            classification=resp_data["classification"],
            agent_notes=resp_data["agent_notes"],
            remediation_notes=resp_data["remediation_notes"],
        )
        session.add(response)

    session.commit()

    return assessment.id, session


def main():
    """Generate and print sample report."""
    print("Generating sample CMMC assessment report...")
    print("=" * 80)
    print()

    # Create sample assessment
    assessment_id, session = create_sample_assessment()

    # Generate report
    report = generate_gap_report(assessment_id, session)

    # Export as Markdown
    markdown_report = export_report_markdown(report)

    print(markdown_report)
    print()
    print("=" * 80)
    print()
    print(f"Report Summary:")
    print(f"- Domain: {report.domain}")
    print(f"- Total Controls: {report.scoring.total_controls}")
    print(f"- Compliance Score: {report.scoring.compliance_percentage:.1f}%")
    print(f"- Status: {report.scoring.traffic_light.upper()}")
    print(f"- Gaps Identified: {len(report.gaps)}")
    print(f"- Recommendations: {len(report.recommendations)}")
    print()

    # Optionally save to file
    output_file = "sample_report.md"
    with open(output_file, "w") as f:
        f.write(markdown_report)
    print(f"✓ Markdown report saved to: {output_file}")

    # Save JSON version
    json_file = "sample_report.json"
    import json as json_module
    with open(json_file, "w") as f:
        json_module.dump(export_report_json(report), f, indent=2)
    print(f"✓ JSON report saved to: {json_file}")

    session.close()


if __name__ == "__main__":
    main()
