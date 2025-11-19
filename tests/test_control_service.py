"""Tests for control service."""

import pytest
from pathlib import Path

from src.services.control_service import ControlService, Control, reset_control_service


@pytest.fixture
def control_service():
    """Create a control service instance for testing."""
    # Reset global instance before each test
    reset_control_service()

    # Use the actual controls.json file
    controls_file = Path(__file__).parent.parent / "src" / "data" / "controls.json"
    service = ControlService(controls_file=str(controls_file))
    yield service

    # Reset after test
    reset_control_service()


class TestControlService:
    """Test ControlService functionality."""

    def test_load_controls(self, control_service):
        """Test that controls are loaded successfully."""
        controls = control_service.get_all_controls()
        assert len(controls) > 0
        assert all(isinstance(c, Control) for c in controls)

    def test_get_control_by_id(self, control_service):
        """Test retrieving a control by ID."""
        control = control_service.get_control_by_id("AC.L2-3.1.1")

        assert control is not None
        assert control.control_id == "AC.L2-3.1.1"
        assert control.domain == "Access Control"
        assert control.title == "Authorized Access Enforcement"
        assert "authorized users" in control.requirement.lower()

    def test_get_nonexistent_control(self, control_service):
        """Test retrieving a control that doesn't exist."""
        control = control_service.get_control_by_id("NONEXISTENT.123")
        assert control is None

    def test_get_controls_by_domain(self, control_service):
        """Test retrieving controls by domain."""
        controls = control_service.get_controls_by_domain("Access Control")

        assert len(controls) > 0
        assert all(c.domain == "Access Control" for c in controls)

        # Verify we have the expected Access Control controls
        control_ids = [c.control_id for c in controls]
        assert "AC.L2-3.1.1" in control_ids
        assert "AC.L2-3.1.2" in control_ids

    def test_get_controls_nonexistent_domain(self, control_service):
        """Test retrieving controls from nonexistent domain."""
        controls = control_service.get_controls_by_domain("Nonexistent Domain")
        assert len(controls) == 0

    def test_get_domains(self, control_service):
        """Test retrieving list of domains."""
        domains = control_service.get_domains()

        assert len(domains) > 0
        assert "Access Control" in domains

    def test_get_control_count_by_domain(self, control_service):
        """Test getting control count for a domain."""
        count = control_service.get_control_count_by_domain("Access Control")

        assert count > 0
        assert isinstance(count, int)

        # Verify it matches actual controls
        controls = control_service.get_controls_by_domain("Access Control")
        assert count == len(controls)

    def test_get_control_count_nonexistent_domain(self, control_service):
        """Test control count for nonexistent domain."""
        count = control_service.get_control_count_by_domain("Nonexistent Domain")
        assert count == 0

    def test_search_controls_by_title(self, control_service):
        """Test searching controls by title keyword."""
        results = control_service.search_controls("access")

        assert len(results) > 0
        assert all("access" in c.title.lower() or "access" in c.requirement.lower() or "access" in c.discussion.lower() for c in results)

    def test_search_controls_with_domain_filter(self, control_service):
        """Test searching controls with domain filter."""
        results = control_service.search_controls("session", domain="Access Control")

        assert len(results) > 0
        assert all(c.domain == "Access Control" for c in results)
        assert all("session" in c.title.lower() or "session" in c.requirement.lower() or "session" in c.discussion.lower() for c in results)

    def test_search_no_results(self, control_service):
        """Test search with no matching results."""
        results = control_service.search_controls("xyznonexistentkeyword123")
        assert len(results) == 0

    def test_get_control_summary(self, control_service):
        """Test getting control summary statistics."""
        summary = control_service.get_control_summary()

        assert "total_controls" in summary
        assert "domains" in summary
        assert "domain_count" in summary

        assert summary["total_controls"] > 0
        assert summary["domain_count"] > 0
        assert isinstance(summary["domains"], dict)

        # Verify Access Control is in summary
        assert "Access Control" in summary["domains"]
        assert summary["domains"]["Access Control"] > 0

    def test_control_data_structure(self, control_service):
        """Test that control data has required fields."""
        control = control_service.get_control_by_id("AC.L2-3.1.1")

        assert control is not None
        assert hasattr(control, "control_id")
        assert hasattr(control, "domain")
        assert hasattr(control, "title")
        assert hasattr(control, "requirement")
        assert hasattr(control, "assessment_objective")
        assert hasattr(control, "discussion")
        assert hasattr(control, "nist_reference")

        # Verify fields are non-empty
        assert len(control.control_id) > 0
        assert len(control.domain) > 0
        assert len(control.title) > 0
        assert len(control.requirement) > 0

    def test_control_immutability(self, control_service):
        """Test that getting controls returns copies, not references."""
        controls1 = control_service.get_all_controls()
        controls2 = control_service.get_all_controls()

        # Modifying one list shouldn't affect the other
        controls1.pop()
        assert len(controls1) != len(controls2)

    def test_access_control_domain_count(self, control_service):
        """Test that we have the expected number of Access Control controls."""
        controls = control_service.get_controls_by_domain("Access Control")

        # We loaded 15 Access Control controls in controls.json
        assert len(controls) == 15

    def test_specific_controls_exist(self, control_service):
        """Test that specific expected controls exist."""
        expected_controls = [
            "AC.L2-3.1.1",  # Authorized Access Enforcement
            "AC.L2-3.1.2",  # Transaction and Function Control
            "AC.L2-3.1.5",  # Least Privilege
            "AC.L2-3.1.12", # Control Remote Access
        ]

        for control_id in expected_controls:
            control = control_service.get_control_by_id(control_id)
            assert control is not None, f"Control {control_id} should exist"
            assert control.domain == "Access Control"
