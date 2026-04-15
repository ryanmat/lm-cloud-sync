# Description: Unit tests for GCP LM group operations.
# Description: Tests payload building, response parsing, and group listing.

"""Unit tests for GCP LM group operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lm_cloud_sync.core.models import CloudProvider, GCPProject
from lm_cloud_sync.providers.gcp.groups import (
    _build_gcp_group_payload,
    _parse_group_response,
    list_gcp_groups,
)


@pytest.fixture()
def sample_project() -> GCPProject:
    """Create a sample GCP project."""
    return GCPProject(
        resource_id="my-project-123",
        display_name="My Project",
        status="ACTIVE",
        project_number="123456789",
    )


@pytest.fixture()
def sample_sa_key() -> dict:
    """Create a sample service account key."""
    return {
        "type": "service_account",
        "project_id": "my-project-123",
        "private_key_id": "key-123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        "client_email": "sa@my-project-123.iam.gserviceaccount.com",
    }


class TestBuildGCPGroupPayload:
    """Tests for building GCP group API payloads."""

    def test_build_payload_defaults(self, sample_project, sample_sa_key) -> None:
        """Build payload with default values."""
        payload = _build_gcp_group_payload(
            resource=sample_project,
            service_account_key=sample_sa_key,
        )
        assert payload["groupType"] == "GCP/GcpRoot"
        assert payload["parentId"] == 1
        assert payload["extra"]["account"]["projectId"] == "my-project-123"
        assert payload["extra"]["account"]["collectorId"] == -2

    def test_build_payload_custom_name_template(self, sample_project, sample_sa_key) -> None:
        """Build payload with custom name template."""
        payload = _build_gcp_group_payload(
            resource=sample_project,
            service_account_key=sample_sa_key,
            name_template="{display_name} ({resource_id})",
        )
        assert payload["name"] == "My Project (my-project-123)"

    def test_build_payload_custom_regions(self, sample_project, sample_sa_key) -> None:
        """Build payload with custom regions."""
        payload = _build_gcp_group_payload(
            resource=sample_project,
            service_account_key=sample_sa_key,
            regions=["europe-west1", "asia-east1"],
        )
        assert payload["extra"]["default"]["monitoringRegions"] == ["europe-west1", "asia-east1"]

    def test_build_payload_custom_parent_id(self, sample_project, sample_sa_key) -> None:
        """Build payload with custom parent group ID."""
        payload = _build_gcp_group_payload(
            resource=sample_project,
            service_account_key=sample_sa_key,
            parent_id=42,
        )
        assert payload["parentId"] == 42


class TestParseGroupResponse:
    """Tests for parsing LM API responses for GCP groups."""

    def test_parse_valid_response(self) -> None:
        """Parse a valid GCP group response."""
        response = {
            "id": 123,
            "name": "GCP - my-project-123",
            "description": "My Project",
            "parentId": 1,
            "groupType": "GCP/GcpRoot",
            "customProperties": [{"name": "env", "value": "prod"}],
            "extra": {
                "account": {
                    "projectId": "my-project-123",
                    "schedule": "0 * * * *",
                }
            },
        }
        group = _parse_group_response(response)
        assert group is not None
        assert group.id == 123
        assert group.resource_id == "my-project-123"
        assert group.name == "GCP - my-project-123"
        assert group.provider == CloudProvider.GCP
        assert group.custom_properties["env"] == "prod"

    def test_parse_response_missing_project_id(self) -> None:
        """Parse response with missing projectId returns None."""
        response = {
            "id": 123,
            "name": "Some Group",
            "extra": {"account": {}},
        }
        group = _parse_group_response(response)
        assert group is None


class TestListGCPGroups:
    """Tests for listing GCP groups."""

    def test_list_groups_flat_response(self) -> None:
        """List groups from flat response shape."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "items": [
                {
                    "id": 1,
                    "name": "GCP - project-alpha",
                    "groupType": "GCP/GcpRoot",
                    "extra": {"account": {"projectId": "project-alpha"}},
                },
            ]
        }
        groups = list_gcp_groups(mock_client)
        assert len(groups) == 1
        assert groups[0].resource_id == "project-alpha"

    def test_list_groups_data_wrapped_response(self) -> None:
        """List groups from data-wrapped response shape."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "data": {
                "items": [
                    {
                        "id": 1,
                        "name": "GCP - project-beta",
                        "groupType": "GCP/GcpRoot",
                        "extra": {"account": {"projectId": "project-beta"}},
                    },
                ]
            }
        }
        groups = list_gcp_groups(mock_client)
        assert len(groups) == 1
        assert groups[0].resource_id == "project-beta"

    def test_list_groups_empty_response(self) -> None:
        """List groups when none exist."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        groups = list_gcp_groups(mock_client)
        assert len(groups) == 0
