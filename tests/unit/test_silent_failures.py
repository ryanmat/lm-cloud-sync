# Description: Tests for silent failure pattern fixes.
# Description: Validates that errors are surfaced instead of silently swallowed.

"""Tests for silent failure pattern fixes."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from lm_cloud_sync.core.exceptions import ConfigurationError, LMAPIError
from lm_cloud_sync.core.lm_client import LogicMonitorClient


class TestLMClientResponseValidation:
    """LM API can return 200 with error payloads. These must be caught."""

    def test_200_with_errmsg_raises(self, httpx_mock: Any) -> None:
        """A 200 response with errmsg field is an error, not success."""
        httpx_mock.add_response(
            status_code=200,
            json={"errmsg": "Authentication token expired"},
        )
        client = LogicMonitorClient(
            company="test", bearer_token=SecretStr("token"), max_retries=0
        )
        with pytest.raises(LMAPIError, match="Authentication token expired"):
            client.get("/device/groups")
        client.close()

    def test_200_with_error_message_raises(self, httpx_mock: Any) -> None:
        """A 200 response with errorMessage field is an error, not success."""
        httpx_mock.add_response(
            status_code=200,
            json={"errorMessage": "Rate limit exceeded", "status": 1429},
        )
        client = LogicMonitorClient(
            company="test", bearer_token=SecretStr("token"), max_retries=0
        )
        with pytest.raises(LMAPIError, match="Rate limit exceeded"):
            client.get("/device/groups")
        client.close()

    def test_200_with_valid_data_returns_normally(self, httpx_mock: Any) -> None:
        """A 200 response with actual data (no error fields) works normally."""
        httpx_mock.add_response(
            status_code=200,
            json={"data": {"items": [{"id": 1, "name": "test"}]}},
        )
        client = LogicMonitorClient(
            company="test", bearer_token=SecretStr("token"), max_retries=0
        )
        result = client.get("/device/groups")
        assert result["data"]["items"][0]["id"] == 1
        client.close()

    def test_malformed_json_response_raises(self, httpx_mock: Any) -> None:
        """A 200 response with non-JSON body raises LMAPIError."""
        httpx_mock.add_response(
            status_code=200,
            text="<html>Load balancer error</html>",
            headers={"content-type": "text/html"},
        )
        client = LogicMonitorClient(
            company="test", bearer_token=SecretStr("token"), max_retries=0
        )
        with pytest.raises(LMAPIError, match="Invalid JSON"):
            client.get("/device/groups")
        client.close()

    def test_empty_response_body_returns_empty_dict(self) -> None:
        """A 200 response with no content returns empty dict."""
        client = LogicMonitorClient(
            company="test", bearer_token=SecretStr("token"), max_retries=0
        )
        with patch.object(client, "_client") as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = None
            mock_http.request.return_value = mock_response
            result = client._request("GET", "/test")
            assert result == {}
        client.close()


class TestParseGroupResponseLogging:
    """_parse_group_response must log warnings, not silently return None."""

    def test_aws_missing_role_arn_logs_warning(self, caplog: Any) -> None:
        """AWS groups without assumedRoleArn should log a warning."""
        from lm_cloud_sync.providers.aws.groups import _parse_group_response

        item: dict[str, Any] = {
            "id": 42,
            "name": "Test Group",
            "extra": {"account": {}},
        }
        with caplog.at_level(logging.WARNING):
            result = _parse_group_response(item)

        assert result is None
        assert any("42" in record.message for record in caplog.records)

    def test_aws_malformed_arn_logs_warning(self, caplog: Any) -> None:
        """AWS groups with malformed ARN should log the issue."""
        from lm_cloud_sync.providers.aws.groups import _parse_group_response

        item: dict[str, Any] = {
            "id": 43,
            "name": "Bad ARN Group",
            "extra": {"account": {"assumedRoleArn": "not-a-real-arn"}},
        }
        with caplog.at_level(logging.WARNING):
            result = _parse_group_response(item)

        assert result is None
        assert any("43" in record.message for record in caplog.records)

    def test_azure_missing_subscription_logs_warning(self, caplog: Any) -> None:
        """Azure groups without subscriptionIds should log a warning."""
        from lm_cloud_sync.providers.azure.groups import _parse_group_response

        item: dict[str, Any] = {
            "id": 44,
            "name": "Test Azure Group",
            "extra": {"account": {}},
        }
        with caplog.at_level(logging.WARNING):
            result = _parse_group_response(item)

        assert result is None
        assert any("44" in record.message for record in caplog.records)

    def test_gcp_missing_project_id_logs_warning(self, caplog: Any) -> None:
        """GCP groups without projectId should log a warning."""
        from lm_cloud_sync.providers.gcp.groups import _parse_group_response

        item: dict[str, Any] = {
            "id": 45,
            "name": "Test GCP Group",
            "extra": {"account": {}},
        }
        with caplog.at_level(logging.WARNING):
            result = _parse_group_response(item)

        assert result is None
        assert any("45" in record.message for record in caplog.records)


class TestAzureCredentialFallback:
    """Azure provider must not silently fall back when partial creds are given."""

    def test_partial_credentials_raise(self) -> None:
        """If user provides some Azure creds but not all, raise immediately."""
        from lm_cloud_sync.core.config import AzureConfig
        from lm_cloud_sync.providers.azure.provider import AzureProvider

        config = AzureConfig(
            enabled=True,
            tenant_id="tenant-123",
            client_id="client-456",
            # client_secret intentionally missing
        )
        provider = AzureProvider(config=config)

        with pytest.raises(ConfigurationError, match="Azure credentials required"):
            provider._get_discovery()

    def test_no_credentials_falls_back_with_log(self, caplog: Any) -> None:
        """If no Azure creds at all, fall back to DefaultAzureCredential with a log."""
        from lm_cloud_sync.core.config import AzureConfig
        from lm_cloud_sync.providers.azure.provider import AzureProvider

        config = AzureConfig(enabled=True)
        provider = AzureProvider(config=config)

        with caplog.at_level(logging.INFO):
            # This may raise if DefaultAzureCredential isn't available,
            # but the important thing is it doesn't raise ConfigurationError
            try:
                provider._get_discovery()
            except Exception as e:
                # Acceptable: DefaultAzureCredential fails in test env
                assert not isinstance(e, ConfigurationError)

        assert any("DefaultAzureCredential" in r.message for r in caplog.records)


class TestSyncExitCodes:
    """sync() failures must result in non-zero exit codes."""

    def test_base_sync_logs_failures(self) -> None:
        """base.py sync() must log exceptions, not just store str(e)."""
        from lm_cloud_sync.providers.base import CloudProviderBase

        # Create a concrete test provider
        class TestProvider(CloudProviderBase):
            @property
            def name(self) -> str:
                return "aws"

            @property
            def provider_type(self) -> str:
                return "aws"

            @property
            def group_type(self) -> str:
                return "AWS/AwsRoot"

            def discover(self, auto_discover: bool = False) -> list:
                from lm_cloud_sync.core.models import CloudProvider, CloudResource
                return [CloudResource(
                    provider=CloudProvider.AWS, resource_id="res-1",
                    display_name="Res 1", status="ACTIVE",
                )]

            def list_integrations(self, client: Any) -> list:
                return []

            def create_integration(self, client: Any, resource: Any, **kwargs: Any) -> Any:
                from lm_cloud_sync.core.exceptions import LMAPIError
                raise LMAPIError("API connection failed", status_code=500)

            def delete_integration(self, client: Any, group_id: int) -> None:
                pass

        provider = TestProvider()
        mock_client = MagicMock()

        with patch("lm_cloud_sync.providers.base.logger") as mock_logger:
            result = provider.sync(mock_client)

        assert result.has_failures
        assert "res-1" in result.failed
        assert "API connection failed" in result.failed["res-1"]
        mock_logger.exception.assert_called_once()


class TestGCPUnknownState:
    """Unknown GCP project states must not default to ACTIVE."""

    def test_unknown_state_logs_warning(self) -> None:
        """Projects with unknown states should be flagged, not treated as ACTIVE."""
        from lm_cloud_sync.providers.gcp.discovery import GCPProjectDiscovery

        discovery = GCPProjectDiscovery.__new__(GCPProjectDiscovery)
        discovery._filters = None

        mock_project = MagicMock()
        mock_project.project_id = "test-proj"
        mock_project.display_name = "Test Project"
        mock_project.state.name = "SUSPENDED"
        mock_project.name = "projects/123"
        mock_project.parent = None
        mock_project.labels = {}
        mock_project.create_time = None

        with patch("lm_cloud_sync.providers.gcp.discovery.logger") as mock_logger:
            discovery._convert_project(mock_project)

        # After fix: unknown state should either skip or warn
        # Current behavior defaults to ACTIVE -- the fix changes this
        mock_logger.warning.assert_called_once()
