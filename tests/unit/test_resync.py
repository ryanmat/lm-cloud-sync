# Description: Tests for the core resync module.
# Description: Validates GET-modify-PUT workflow for triggering LM cloud sync engine.

"""Tests for core resync module."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import MagicMock

import pytest

from lm_cloud_sync.core.exceptions import LMAPIError


def _make_group_payload(
    group_id: int = 100,
    name: str = "AWS - 123456789",
    group_type: str = "AWS/AwsRoot",
    extra: dict[str, Any] | None = None,
    sub_groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a realistic LM device group payload for testing."""
    return {
        "id": group_id,
        "name": name,
        "description": "Test cloud root group",
        "parentId": 1,
        "groupType": group_type,
        "customProperties": [
            {"name": "lm.cloud.managed_by", "value": "lm-cloud-sync"},
        ],
        "extra": extra if extra is not None else {
            "account": {
                "assumedRoleArn": "arn:aws:iam::123456789:role/LMRole",
                "externalId": "ext-123",
                "collectorId": -2,
                "schedule": "0 * * * *",
            },
            "default": {
                "useDefault": True,
                "selectAll": False,
                "monitoringRegions": ["us-east-1", "us-west-2"],
                "tags": [],
                "nameFilter": [],
                "deadOperation": "KEEP_7_DAYS",
                "disableTerminatedHostAlerting": True,
            },
            "services": {},
        },
        "subGroups": sub_groups if sub_groups is not None else [
            {"id": 101, "name": "EC2 Instances"},
            {"id": 102, "name": "RDS Databases"},
        ],
    }


def _make_azure_group_payload(group_id: int = 200) -> dict[str, Any]:
    """Build an Azure group payload with masked secretKey."""
    return _make_group_payload(
        group_id=group_id,
        name="Azure - sub-abc-123",
        group_type="Azure/AzureRoot",
        extra={
            "account": {
                "tenantId": "tenant-123",
                "clientId": "client-456",
                "secretKey": "****",
                "subscriptionIds": "sub-abc-123",
                "collectorId": -4,
                "schedule": "0 * * * *",
            },
            "default": {
                "useDefault": True,
                "selectAll": False,
                "monitoringRegions": ["eastus"],
                "tags": [],
                "nameFilter": [],
                "deadOperation": "KEEP_7_DAYS",
                "disableTerminatedHostAlerting": True,
            },
            "services": {},
        },
    )


class TestPrepareResyncPayload:
    """Tests for prepare_resync_payload function."""

    def test_strips_subgroups(self) -> None:
        """SubGroups is read-only and must be stripped before PUT."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload()
        assert "subGroups" in payload

        result = prepare_resync_payload(payload)
        assert "subGroups" not in result

    def test_preserves_required_fields(self) -> None:
        """All required fields for the PUT must survive preparation."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload()
        result = prepare_resync_payload(payload)

        assert result["name"] == "AWS - 123456789"
        assert result["groupType"] == "AWS/AwsRoot"
        assert result["parentId"] == 1
        assert "extra" in result
        assert result["extra"]["account"]["assumedRoleArn"] == "arn:aws:iam::123456789:role/LMRole"

    def test_does_not_mutate_original(self) -> None:
        """Preparation must deep-copy, not modify the input."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload()
        original = copy.deepcopy(payload)
        prepare_resync_payload(payload, extra_modifications={"default": {"selectAll": True}})

        assert payload == original

    def test_merges_extra_modifications(self) -> None:
        """Extra modifications are deep-merged into the extra field."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload()
        modifications = {
            "default": {"monitoringRegions": ["us-east-1", "eu-west-1"]},
            "services": {"EC2": {"useDefault": False, "selectAll": True}},
        }

        result = prepare_resync_payload(payload, extra_modifications=modifications)

        assert result["extra"]["default"]["monitoringRegions"] == ["us-east-1", "eu-west-1"]
        assert result["extra"]["services"]["EC2"]["selectAll"] is True
        # Unchanged nested values preserved
        assert result["extra"]["default"]["useDefault"] is True
        assert result["extra"]["account"]["assumedRoleArn"] == "arn:aws:iam::123456789:role/LMRole"

    def test_no_modifications_passes_through(self) -> None:
        """Without modifications, payload is identical minus read-only fields."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload()
        result = prepare_resync_payload(payload)

        expected = copy.deepcopy(payload)
        del expected["subGroups"]
        assert result == expected

    def test_empty_extra_field(self) -> None:
        """Groups with empty extra should not crash."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload(extra={})
        result = prepare_resync_payload(payload)
        assert result["extra"] == {}

    def test_modifications_on_empty_extra(self) -> None:
        """Modifications applied to empty extra create the structure."""
        from lm_cloud_sync.core.resync import prepare_resync_payload

        payload = _make_group_payload(extra={})
        modifications = {"default": {"monitoringRegions": ["us-east-1"]}}

        result = prepare_resync_payload(payload, extra_modifications=modifications)
        assert result["extra"]["default"]["monitoringRegions"] == ["us-east-1"]


class TestCheckMaskedCredentials:
    """Tests for check_masked_credentials function."""

    def test_detects_masked_secret_key(self) -> None:
        """Masked Azure secretKey must be detected."""
        from lm_cloud_sync.core.resync import check_masked_credentials

        payload = _make_azure_group_payload()
        masked = check_masked_credentials(payload)
        assert "secretKey" in masked

    def test_clean_payload_returns_empty(self) -> None:
        """AWS payload without masked values returns empty list."""
        from lm_cloud_sync.core.resync import check_masked_credentials

        payload = _make_group_payload()
        masked = check_masked_credentials(payload)
        assert masked == []

    def test_no_account_section(self) -> None:
        """Payload with no extra.account should not crash."""
        from lm_cloud_sync.core.resync import check_masked_credentials

        payload = _make_group_payload(extra={})
        masked = check_masked_credentials(payload)
        assert masked == []

    def test_multiple_masked_fields(self) -> None:
        """All masked fields should be reported."""
        from lm_cloud_sync.core.resync import check_masked_credentials

        payload = _make_group_payload(extra={
            "account": {"secretKey": "****", "password": "****", "apiToken": "real-value"},
        })
        masked = check_masked_credentials(payload)
        assert "secretKey" in masked
        assert "password" in masked
        assert "apiToken" not in masked


class TestListCloudRootGroups:
    """Tests for list_cloud_root_groups function."""

    def test_single_provider(self) -> None:
        """Querying a single provider filters by that groupType."""
        from lm_cloud_sync.core.resync import list_cloud_root_groups

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "data": {"items": [_make_group_payload()]},
        }

        list_cloud_root_groups(mock_client, provider="aws")

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert 'groupType:"AWS/AwsRoot"' in call_args.kwargs.get("params", call_args.args[1] if len(call_args.args) > 1 else {}).get("filter", "")

    def test_all_providers(self) -> None:
        """Querying all providers makes three API calls."""
        from lm_cloud_sync.core.resync import list_cloud_root_groups

        mock_client = MagicMock()
        mock_client.get.return_value = {"data": {"items": []}}

        list_cloud_root_groups(mock_client, provider=None)

        assert mock_client.get.call_count == 3

    def test_returns_group_dicts(self) -> None:
        """Returns raw group dicts from the API response."""
        from lm_cloud_sync.core.resync import list_cloud_root_groups

        group = _make_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = {"data": {"items": [group]}}

        groups = list_cloud_root_groups(mock_client, provider="aws")

        assert len(groups) == 1
        assert groups[0]["id"] == 100
        assert groups[0]["groupType"] == "AWS/AwsRoot"

    def test_zero_groups_returned(self) -> None:
        """Empty result set returns empty list."""
        from lm_cloud_sync.core.resync import list_cloud_root_groups

        mock_client = MagicMock()
        mock_client.get.return_value = {"data": {"items": []}}

        groups = list_cloud_root_groups(mock_client, provider="gcp")
        assert groups == []

    def test_invalid_provider_raises(self) -> None:
        """Unknown provider name raises ValueError."""
        from lm_cloud_sync.core.resync import list_cloud_root_groups

        mock_client = MagicMock()
        with pytest.raises(ValueError, match="Unknown provider"):
            list_cloud_root_groups(mock_client, provider="oracle")


class TestResyncGroup:
    """Tests for resync_group function."""

    def test_dry_run_skips_put(self) -> None:
        """Dry run performs GET but not PUT."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group

        result = resync_group(mock_client, group_id=100, dry_run=True)

        mock_client.get.assert_called_once()
        mock_client.put.assert_not_called()
        assert result.status == "dry_run"
        assert result.group_id == 100
        assert result.group_name == "AWS - 123456789"

    def test_success_returns_test_results(self) -> None:
        """Successful PUT returns test result fields from response."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        put_response = copy.deepcopy(group)
        put_response["awsTestResult"] = "OK: 3 regions validated"

        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = put_response

        result = resync_group(mock_client, group_id=100)

        mock_client.get.assert_called_once()
        mock_client.put.assert_called_once()
        assert result.status == "success"
        assert result.test_results["awsTestResult"] == "OK: 3 regions validated"

    def test_put_payload_has_no_subgroups(self) -> None:
        """PUT payload must not contain subGroups."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = group

        resync_group(mock_client, group_id=100)

        put_call = mock_client.put.call_args
        put_payload = put_call.kwargs.get("json", put_call.args[1] if len(put_call.args) > 1 else {})
        assert "subGroups" not in put_payload

    def test_api_error_returns_failed(self) -> None:
        """PUT failure returns failed status with error message."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.side_effect = LMAPIError("Bad Request", status_code=400)

        result = resync_group(mock_client, group_id=100)

        assert result.status == "failed"
        assert "Bad Request" in (result.error or "")

    def test_extra_modifications_applied(self) -> None:
        """Modifications to extra field are included in PUT payload."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = group

        resync_group(
            mock_client,
            group_id=100,
            extra_modifications={"default": {"monitoringRegions": ["eu-west-1"]}},
        )

        put_call = mock_client.put.call_args
        put_payload = put_call.kwargs.get("json", put_call.args[1] if len(put_call.args) > 1 else {})
        assert put_payload["extra"]["default"]["monitoringRegions"] == ["eu-west-1"]

    def test_masked_credentials_reported_as_warning(self) -> None:
        """Azure groups with masked credentials report warning with field names."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_azure_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = group

        result = resync_group(mock_client, group_id=200)

        assert "secretKey" in result.masked_fields

    def test_credential_override_replaces_masked_value(self) -> None:
        """Credential overrides replace masked values in the PUT payload."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_azure_group_payload()
        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = group

        resync_group(
            mock_client,
            group_id=200,
            credential_overrides={"secretKey": "real-secret-value"},
        )

        put_call = mock_client.put.call_args
        put_payload = put_call.kwargs.get("json", put_call.args[1] if len(put_call.args) > 1 else {})
        assert put_payload["extra"]["account"]["secretKey"] == "real-secret-value"

    def test_get_failure_returns_failed(self) -> None:
        """GET failure returns failed status."""
        from lm_cloud_sync.core.resync import resync_group

        mock_client = MagicMock()
        mock_client.get.side_effect = LMAPIError("Not Found", status_code=404)

        result = resync_group(mock_client, group_id=999)

        assert result.status == "failed"
        assert "Not Found" in (result.error or "")
        mock_client.put.assert_not_called()

    def test_failed_test_result_sets_warning_status(self) -> None:
        """PUT response with failure in test results should set status=warning."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        put_response = copy.deepcopy(group)
        put_response["awsTestResult"] = "FAIL: credentials invalid"

        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = put_response

        result = resync_group(mock_client, group_id=100)

        assert result.status == "warning"
        assert result.test_results["awsTestResult"] == "FAIL: credentials invalid"

    def test_successful_test_result_keeps_success_status(self) -> None:
        """PUT response with passing test results should keep status=success."""
        from lm_cloud_sync.core.resync import resync_group

        group = _make_group_payload()
        put_response = copy.deepcopy(group)
        put_response["awsTestResult"] = "OK: credentials valid"

        mock_client = MagicMock()
        mock_client.get.return_value = group
        mock_client.put.return_value = put_response

        result = resync_group(mock_client, group_id=100)

        assert result.status == "success"
