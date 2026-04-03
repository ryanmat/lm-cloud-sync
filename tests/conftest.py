"""Pytest fixtures for lm-cloud-sync tests."""

import pytest
from pydantic import SecretStr

from lm_cloud_sync.core.config import GCPConfig, LogicMonitorConfig, Settings
from lm_cloud_sync.core.models import GCPProject


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        logicmonitor=LogicMonitorConfig(
            company="test-company",
            bearer_token=SecretStr("test-token"),
            auth_method="bearer",
            parent_group_id=1,
        ),
        gcp=GCPConfig(enabled=True),
    )


@pytest.fixture
def mock_gcp_project() -> GCPProject:
    """Create a mock GCP project for testing."""
    return GCPProject(
        resource_id="test-project-123",
        display_name="Test Project",
        status="ACTIVE",
        project_number="123456789",
        labels={"env": "test"},
    )


@pytest.fixture
def mock_gcp_projects() -> list[GCPProject]:
    """Create multiple mock GCP projects for testing."""
    return [
        GCPProject(
            resource_id="project-alpha",
            display_name="Project Alpha",
            status="ACTIVE",
            project_number="111111111",
        ),
        GCPProject(
            resource_id="project-beta",
            display_name="Project Beta",
            status="ACTIVE",
            project_number="222222222",
        ),
        GCPProject(
            resource_id="project-gamma",
            display_name="Project Gamma",
            status="ACTIVE",
            project_number="333333333",
        ),
    ]
