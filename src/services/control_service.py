"""Service for loading and querying CMMC control data."""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Control(BaseModel):
    """CMMC control data model."""

    control_id: str = Field(..., description="Control identifier (e.g., AC.L2-3.1.1)")
    domain: str = Field(..., description="CMMC domain (e.g., Access Control)")
    title: str = Field(..., description="Control title")
    requirement: str = Field(..., description="Control requirement text")
    assessment_objective: str = Field(..., description="What assessor should determine")
    discussion: str = Field(..., description="Additional context and guidance")
    nist_reference: str = Field(..., description="NIST SP 800-171 reference")


class ControlService:
    """Service for managing CMMC control data."""

    def __init__(self, controls_file: Optional[str] = None):
        """
        Initialize control service.

        Args:
            controls_file: Path to controls.json file (defaults to src/data/controls.json)
        """
        if controls_file is None:
            # Default to src/data/controls.json relative to this file
            current_dir = Path(__file__).parent.parent
            controls_file = current_dir / "data" / "controls.json"

        self.controls_file = Path(controls_file)
        self._controls: List[Control] = []
        self._controls_by_id: Dict[str, Control] = {}
        self._controls_by_domain: Dict[str, List[Control]] = {}

        self._load_controls()

    def _load_controls(self) -> None:
        """Load controls from JSON file."""
        if not self.controls_file.exists():
            raise FileNotFoundError(f"Controls file not found: {self.controls_file}")

        with open(self.controls_file, "r") as f:
            controls_data = json.load(f)

        # Parse and validate controls
        self._controls = [Control(**control_data) for control_data in controls_data]

        # Build indexes for fast lookups
        for control in self._controls:
            self._controls_by_id[control.control_id] = control

            if control.domain not in self._controls_by_domain:
                self._controls_by_domain[control.domain] = []
            self._controls_by_domain[control.domain].append(control)

    def get_all_controls(self) -> List[Control]:
        """
        Get all controls.

        Returns:
            List of all controls
        """
        return self._controls.copy()

    def get_control_by_id(self, control_id: str) -> Optional[Control]:
        """
        Get a control by its ID.

        Args:
            control_id: Control identifier (e.g., "AC.L2-3.1.1")

        Returns:
            Control if found, None otherwise
        """
        return self._controls_by_id.get(control_id)

    def get_controls_by_domain(self, domain: str) -> List[Control]:
        """
        Get all controls for a specific domain.

        Args:
            domain: CMMC domain name (e.g., "Access Control")

        Returns:
            List of controls in the domain
        """
        return self._controls_by_domain.get(domain, []).copy()

    def get_domains(self) -> List[str]:
        """
        Get list of all available domains.

        Returns:
            List of domain names
        """
        return list(self._controls_by_domain.keys())

    def get_control_count_by_domain(self, domain: str) -> int:
        """
        Get the number of controls in a domain.

        Args:
            domain: CMMC domain name

        Returns:
            Number of controls in the domain
        """
        return len(self._controls_by_domain.get(domain, []))

    def search_controls(self, query: str, domain: Optional[str] = None) -> List[Control]:
        """
        Search controls by keyword.

        Args:
            query: Search query (searches title, requirement, discussion)
            domain: Optional domain filter

        Returns:
            List of matching controls
        """
        query_lower = query.lower()
        results = []

        controls_to_search = (
            self._controls_by_domain.get(domain, [])
            if domain
            else self._controls
        )

        for control in controls_to_search:
            if (
                query_lower in control.title.lower()
                or query_lower in control.requirement.lower()
                or query_lower in control.discussion.lower()
            ):
                results.append(control)

        return results

    def get_control_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about controls.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_controls": len(self._controls),
            "domains": {
                domain: len(controls)
                for domain, controls in self._controls_by_domain.items()
            },
            "domain_count": len(self._controls_by_domain),
        }


# Global service instance (singleton pattern)
_control_service: Optional[ControlService] = None


def get_control_service(controls_file: Optional[str] = None) -> ControlService:
    """
    Get or create the global control service instance.

    Args:
        controls_file: Path to controls.json file (only used on first call)

    Returns:
        ControlService instance
    """
    global _control_service

    if _control_service is None:
        _control_service = ControlService(controls_file=controls_file)

    return _control_service


def reset_control_service() -> None:
    """Reset the global control service instance (for testing)."""
    global _control_service
    _control_service = None
