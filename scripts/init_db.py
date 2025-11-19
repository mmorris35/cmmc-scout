#!/usr/bin/env python3
"""
Database initialization script for CMMC Scout.

Usage:
    python scripts/init_db.py [--drop]

This script will:
1. Create all database tables
2. Seed demo user
3. Verify control data can be loaded
"""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.models import init_db, get_session_maker, User
from src.services import get_control_service

load_dotenv()


def seed_demo_user(session: Session) -> User:
    """Create a demo user for testing."""
    # Check if demo user already exists
    existing_user = session.query(User).filter_by(auth0_id="demo_user_auth0_id").first()

    if existing_user:
        print(f"   Demo user already exists: {existing_user.email}")
        return existing_user

    # Create demo user
    demo_user = User(
        id=uuid4(),
        auth0_id="demo_user_auth0_id",
        email="demo@cmmcscout.com",
        role="assessor",
    )

    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)

    print(f"   ✅ Created demo user: {demo_user.email} (role: {demo_user.role})")
    return demo_user


def verify_controls() -> None:
    """Verify control data can be loaded."""
    control_service = get_control_service()
    summary = control_service.get_control_summary()

    print(f"   ✅ Loaded {summary['total_controls']} controls")
    print(f"   ✅ {summary['domain_count']} domain(s) available:")
    for domain, count in summary['domains'].items():
        print(f"      - {domain}: {count} controls")


def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(description="Initialize CMMC Scout database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating (WARNING: destructive!)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🗄️  CMMC Scout Database Initialization")
    print("=" * 80)

    if args.drop:
        print("\n⚠️  WARNING: Dropping all existing tables!")
        response = input("   Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("   Aborted.")
            return
        print()

    # Initialize database
    print("1️⃣  Creating database tables...")
    try:
        engine = init_db(drop_all=args.drop)
        print(f"   ✅ Tables created successfully")
        print(f"   Database: {engine.url}")
    except Exception as e:
        print(f"   ❌ Failed to create tables: {e}")
        sys.exit(1)

    # Seed demo user
    print("\n2️⃣  Seeding demo user...")
    try:
        SessionMaker = get_session_maker()
        with SessionMaker() as session:
            demo_user = seed_demo_user(session)
    except Exception as e:
        print(f"   ❌ Failed to seed demo user: {e}")
        sys.exit(1)

    # Verify controls
    print("\n3️⃣  Verifying control data...")
    try:
        verify_controls()
    except Exception as e:
        print(f"   ❌ Failed to load controls: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ Database initialization complete!")
    print("=" * 80)

    print("\n📊 Database Summary:")
    print(f"   Tables: users, assessments, control_responses")
    print(f"   Demo User: demo@cmmcscout.com (Auth0 ID: demo_user_auth0_id)")
    print(f"   Controls: 15 Access Control domain controls loaded")

    print("\n💡 Next Steps:")
    print("   1. Start the API server: uvicorn src.main:app --reload")
    print("   2. View API docs: http://localhost:8000/docs")
    print("   3. Run tests: pytest --cov=src")

    print()


if __name__ == "__main__":
    main()
