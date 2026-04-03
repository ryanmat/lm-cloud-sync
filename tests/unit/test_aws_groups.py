# Description: Unit tests for AWS LM group operations.

from unittest.mock import MagicMock

import pytest

from lm_cloud_sync.core.models import AWSAccount, CloudProvider
from lm_cloud_sync.providers.aws.groups import (
    _build_aws_group_payload,
    _parse_group_response,
    list_aws_groups,
)


class TestBuildAWSGroupPayload:
    """Tests for building AWS group API payloads."""

    @pytest.fixture
    def sample_account(self):
        """Create a sample AWS account."""
        return AWSAccount(
            resource_id="123456789012",
            display_name="Production Account",
            status="ACTIVE",
            email="prod@example.com",
        )

    def test_build_payload_defaults(self, sample_account):
        """Test building payload with default values."""
        payload = _build_aws_group_payload(
            resource=sample_account,
            assumed_role_arn="arn:aws:iam::123456789012:role/LogicMonitorRole",
            external_id="ext-123",
        )

        assert payload["groupType"] == "AWS/AwsRoot"
        assert payload["name"] == "AWS - 123456789012"
        assert payload["parentId"] == 1
        assert payload["extra"]["account"]["assumedRoleArn"] == "arn:aws:iam::123456789012:role/LogicMonitorRole"
        assert payload["extra"]["account"]["externalId"] == "ext-123"
        assert payload["extra"]["account"]["collectorId"] == -2
        assert "us-east-1" in payload["extra"]["default"]["monitoringRegions"]

    def test_build_payload_custom_name_template(self, sample_account):
        """Test building payload with custom name template."""
        payload = _build_aws_group_payload(
            resource=sample_account,
            assumed_role_arn="arn:aws:iam::123456789012:role/LMRole",
            external_id="ext-123",
            name_template="{display_name} ({resource_id})",
        )

        assert payload["name"] == "Production Account (123456789012)"

    def test_build_payload_custom_regions(self, sample_account):
        """Test building payload with custom regions."""
        payload = _build_aws_group_payload(
            resource=sample_account,
            assumed_role_arn="arn:aws:iam::123456789012:role/LMRole",
            external_id="ext-123",
            regions=["eu-west-1", "ap-southeast-1"],
        )

        assert payload["extra"]["default"]["monitoringRegions"] == ["eu-west-1", "ap-southeast-1"]

    def test_build_payload_custom_services(self, sample_account):
        """Test building payload with custom services."""
        payload = _build_aws_group_payload(
            resource=sample_account,
            assumed_role_arn="arn:aws:iam::123456789012:role/LMRole",
            external_id="ext-123",
            services=["EC2", "Lambda", "DynamoDB"],
        )

        services = payload["extra"]["services"]
        assert "EC2" in services
        assert "Lambda" in services
        assert "DynamoDB" in services

    def test_build_payload_custom_properties(self, sample_account):
        """Test building payload with custom properties."""
        payload = _build_aws_group_payload(
            resource=sample_account,
            assumed_role_arn="arn:aws:iam::123456789012:role/LMRole",
            external_id="ext-123",
            custom_properties={"env": "production", "team": "platform"},
        )

        props = {p["name"]: p["value"] for p in payload["customProperties"]}
        assert props["env"] == "production"
        assert props["team"] == "platform"


class TestParseGroupResponse:
    """Tests for parsing LM API responses."""

    def test_parse_valid_response(self):
        """Test parsing a valid AWS group response."""
        response = {
            "id": 123,
            "name": "AWS - 123456789012",
            "description": "Production Account",
            "parentId": 1,
            "groupType": "AWS/AwsRoot",
            "customProperties": [
                {"name": "env", "value": "prod"},
            ],
            "extra": {
                "account": {
                    "assumedRoleArn": "arn:aws:iam::123456789012:role/LogicMonitorRole",
                    "externalId": "ext-123",
                    "schedule": "0 * * * *",
                }
            },
        }

        group = _parse_group_response(response)

        assert group is not None
        assert group.id == 123
        assert group.resource_id == "123456789012"
        assert group.name == "AWS - 123456789012"
        assert group.provider == CloudProvider.AWS
        assert group.custom_properties["env"] == "prod"

    def test_parse_response_missing_role_arn(self):
        """Test parsing response with missing role ARN returns None."""
        response = {
            "id": 123,
            "name": "Some Group",
            "extra": {"account": {}},
        }

        group = _parse_group_response(response)
        assert group is None

    def test_parse_response_extracts_account_id_from_arn(self):
        """Test that account ID is correctly extracted from role ARN."""
        response = {
            "id": 123,
            "name": "AWS Account",
            "extra": {
                "account": {
                    "assumedRoleArn": "arn:aws:iam::987654321098:role/CustomRole",
                }
            },
        }

        group = _parse_group_response(response)
        assert group.resource_id == "987654321098"


class TestListAWSGroups:
    """Tests for listing AWS groups."""

    def test_list_groups_returns_aws_groups(self):
        """Test listing AWS groups from LM API."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "items": [
                {
                    "id": 1,
                    "name": "AWS - 111111111111",
                    "groupType": "AWS/AwsRoot",
                    "extra": {
                        "account": {
                            "assumedRoleArn": "arn:aws:iam::111111111111:role/LMRole",
                        }
                    },
                },
                {
                    "id": 2,
                    "name": "AWS - 222222222222",
                    "groupType": "AWS/AwsRoot",
                    "extra": {
                        "account": {
                            "assumedRoleArn": "arn:aws:iam::222222222222:role/LMRole",
                        }
                    },
                },
            ]
        }

        groups = list_aws_groups(mock_client)

        assert len(groups) == 2
        assert groups[0].resource_id == "111111111111"
        assert groups[1].resource_id == "222222222222"

        # Verify API was called correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "device/groups" in call_args[0]
        assert 'groupType:"AWS/AwsRoot"' in call_args[1]["params"]["filter"]

    def test_list_groups_empty_response(self):
        """Test listing groups when none exist."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}

        groups = list_aws_groups(mock_client)

        assert len(groups) == 0
