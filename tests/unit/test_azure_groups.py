# Unit tests for Azure LM group operations.

from unittest.mock import MagicMock

import pytest

from lm_cloud_sync.core.models import AzureSubscription, CloudProvider
from lm_cloud_sync.providers.azure.groups import (
    _build_azure_group_payload,
    _parse_group_response,
    list_azure_groups,
)


class TestBuildAzureGroupPayload:
    """Tests for building Azure group API payloads."""

    @pytest.fixture
    def sample_subscription(self):
        """Create a sample Azure subscription."""
        return AzureSubscription(
            resource_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            display_name="Production Subscription",
            status="Enabled",
            tenant_id="tenant-123",
        )

    def test_build_payload_defaults(self, sample_subscription):
        """Test building payload with default values."""
        payload = _build_azure_group_payload(
            resource=sample_subscription,
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="secret-789",
        )

        assert payload["groupType"] == "Azure/AzureRoot"
        assert payload["name"] == "Azure - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        assert payload["parentId"] == 1
        assert payload["extra"]["account"]["tenantId"] == "tenant-123"
        assert payload["extra"]["account"]["clientId"] == "client-456"
        assert payload["extra"]["account"]["secretKey"] == "secret-789"
        assert payload["extra"]["account"]["subscriptionIds"] == "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        assert payload["extra"]["account"]["collectorId"] == -4
        assert "eastus" in payload["extra"]["default"]["monitoringRegions"]

    def test_build_payload_custom_name_template(self, sample_subscription):
        """Test building payload with custom name template."""
        payload = _build_azure_group_payload(
            resource=sample_subscription,
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="secret-789",
            name_template="{display_name}",
        )

        assert payload["name"] == "Production Subscription"

    def test_build_payload_custom_regions(self, sample_subscription):
        """Test building payload with custom regions."""
        payload = _build_azure_group_payload(
            resource=sample_subscription,
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="secret-789",
            regions=["northeurope", "westeurope"],
        )

        assert payload["extra"]["default"]["monitoringRegions"] == ["northeurope", "westeurope"]

    def test_build_payload_custom_services(self, sample_subscription):
        """Test building payload with custom services."""
        payload = _build_azure_group_payload(
            resource=sample_subscription,
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="secret-789",
            services=["VIRTUALMACHINE", "APPSERVICE", "FUNCTIONS"],
        )

        services = payload["extra"]["services"]
        assert "VIRTUALMACHINE" in services
        assert "APPSERVICE" in services
        assert "FUNCTIONS" in services

    def test_build_payload_custom_properties(self, sample_subscription):
        """Test building payload with custom properties."""
        payload = _build_azure_group_payload(
            resource=sample_subscription,
            tenant_id="tenant-123",
            client_id="client-456",
            client_secret="secret-789",
            custom_properties={"env": "production", "team": "platform"},
        )

        props = {p["name"]: p["value"] for p in payload["customProperties"]}
        assert props["env"] == "production"
        assert props["team"] == "platform"


class TestParseGroupResponse:
    """Tests for parsing LM API responses."""

    def test_parse_valid_response(self):
        """Test parsing a valid Azure group response."""
        response = {
            "id": 123,
            "name": "Azure - sub-123",
            "description": "Production Subscription",
            "parentId": 1,
            "groupType": "Azure/AzureRoot",
            "customProperties": [
                {"name": "env", "value": "prod"},
            ],
            "extra": {
                "account": {
                    "tenantId": "tenant-123",
                    "clientId": "client-456",
                    "subscriptionIds": "sub-123",
                    "schedule": "0 * * * *",
                }
            },
        }

        group = _parse_group_response(response)

        assert group is not None
        assert group.id == 123
        assert group.resource_id == "sub-123"
        assert group.name == "Azure - sub-123"
        assert group.provider == CloudProvider.AZURE
        assert group.custom_properties["env"] == "prod"

    def test_parse_response_missing_subscription_ids(self):
        """Test parsing response with missing subscriptionIds returns None."""
        response = {
            "id": 123,
            "name": "Some Group",
            "extra": {"account": {}},
        }

        group = _parse_group_response(response)
        assert group is None

    def test_parse_response_multiple_subscriptions(self):
        """Test that first subscription ID is extracted from comma-separated list."""
        response = {
            "id": 123,
            "name": "Azure Multi",
            "extra": {
                "account": {
                    "subscriptionIds": "sub-1, sub-2, sub-3",
                }
            },
        }

        group = _parse_group_response(response)
        assert group.resource_id == "sub-1"


class TestListAzureGroups:
    """Tests for listing Azure groups."""

    def test_list_groups_returns_azure_groups(self):
        """Test listing Azure groups from LM API."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "items": [
                {
                    "id": 1,
                    "name": "Azure - sub-1",
                    "groupType": "Azure/AzureRoot",
                    "extra": {
                        "account": {
                            "subscriptionIds": "sub-1",
                        }
                    },
                },
                {
                    "id": 2,
                    "name": "Azure - sub-2",
                    "groupType": "Azure/AzureRoot",
                    "extra": {
                        "account": {
                            "subscriptionIds": "sub-2",
                        }
                    },
                },
            ]
        }

        groups = list_azure_groups(mock_client)

        assert len(groups) == 2
        assert groups[0].resource_id == "sub-1"
        assert groups[1].resource_id == "sub-2"

        # Verify API was called correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "device/groups" in call_args[0]
        assert 'groupType:"Azure/AzureRoot"' in call_args[1]["params"]["filter"]

    def test_list_groups_empty_response(self):
        """Test listing groups when none exist."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}

        groups = list_azure_groups(mock_client)

        assert len(groups) == 0
