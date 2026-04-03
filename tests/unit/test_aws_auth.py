# Description: Unit tests for AWS authentication helpers.

from unittest.mock import MagicMock

import pytest

from lm_cloud_sync.core.exceptions import LMAPIError
from lm_cloud_sync.providers.aws.auth import (
    LM_AWS_ACCOUNT_ID,
    LM_AWS_PRINCIPAL,
    build_role_arn,
    get_external_id,
    get_permissions_policy,
    get_trust_policy,
)


class TestBuildRoleArn:
    """Tests for building IAM role ARNs."""

    def test_build_default_role_arn(self):
        """Test building role ARN with default role name."""
        arn = build_role_arn("123456789012")
        assert arn == "arn:aws:iam::123456789012:role/LogicMonitorRole"

    def test_build_custom_role_arn(self):
        """Test building role ARN with custom role name."""
        arn = build_role_arn("123456789012", "CustomLMRole")
        assert arn == "arn:aws:iam::123456789012:role/CustomLMRole"


class TestGetExternalId:
    """Tests for getting external ID from LogicMonitor API."""

    def test_get_external_id_success(self):
        """Test successfully getting external ID."""
        mock_client = MagicMock()
        mock_client.get.return_value = {"externalId": "lm-ext-abc123"}

        external_id = get_external_id(mock_client)

        assert external_id == "lm-ext-abc123"
        mock_client.get.assert_called_once_with("aws/externalId")

    def test_get_external_id_missing(self):
        """Test error when external ID is missing from response."""
        mock_client = MagicMock()
        mock_client.get.return_value = {}

        with pytest.raises(LMAPIError) as exc_info:
            get_external_id(mock_client)

        assert "external id" in str(exc_info.value).lower()


class TestGetTrustPolicy:
    """Tests for generating IAM trust policies."""

    def test_trust_policy_structure(self):
        """Test trust policy has correct structure."""
        policy = get_trust_policy("ext-123")

        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1

        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        assert statement["Action"] == "sts:AssumeRole"
        assert statement["Principal"]["AWS"] == LM_AWS_PRINCIPAL

    def test_trust_policy_external_id_condition(self):
        """Test trust policy includes external ID condition."""
        policy = get_trust_policy("my-external-id")

        condition = policy["Statement"][0]["Condition"]
        assert condition["StringEquals"]["sts:ExternalId"] == "my-external-id"

    def test_trust_policy_lm_account(self):
        """Test trust policy uses LogicMonitor's AWS account."""
        # Verify LM account ID constant
        assert LM_AWS_ACCOUNT_ID == "282028653949"
        assert LM_AWS_PRINCIPAL == f"arn:aws:iam::{LM_AWS_ACCOUNT_ID}:root"


class TestGetPermissionsPolicy:
    """Tests for generating IAM permissions policies."""

    def test_permissions_policy_structure(self):
        """Test permissions policy has correct structure."""
        policy = get_permissions_policy()

        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1
        assert policy["Statement"][0]["Effect"] == "Allow"
        assert policy["Statement"][0]["Resource"] == "*"

    def test_permissions_policy_includes_ec2(self):
        """Test permissions policy includes EC2 permissions."""
        policy = get_permissions_policy()
        actions = policy["Statement"][0]["Action"]

        assert "ec2:Describe*" in actions

    def test_permissions_policy_includes_rds(self):
        """Test permissions policy includes RDS permissions."""
        policy = get_permissions_policy()
        actions = policy["Statement"][0]["Action"]

        assert "rds:Describe*" in actions
        assert "rds:ListTagsForResource" in actions

    def test_permissions_policy_includes_cloudwatch(self):
        """Test permissions policy includes CloudWatch permissions."""
        policy = get_permissions_policy()
        actions = policy["Statement"][0]["Action"]

        assert "cloudwatch:GetMetricData" in actions
        assert "cloudwatch:GetMetricStatistics" in actions
        assert "cloudwatch:ListMetrics" in actions
