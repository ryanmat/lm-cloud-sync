# Description: Unit tests for AWS account discovery.

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from lm_cloud_sync.core.exceptions import DiscoveryError
from lm_cloud_sync.providers.aws.discovery import AWSAccountDiscovery


class TestAWSAccountDiscovery:
    """Tests for AWS account discovery."""

    @pytest.fixture
    def mock_org_client(self):
        """Create a mock Organizations client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def mock_sts_client(self):
        """Create a mock STS client."""
        client = MagicMock()
        client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test",
            "UserId": "AIDAEXAMPLE",
        }
        return client

    @pytest.fixture
    def discovery(self, mock_org_client, mock_sts_client):
        """Create a discovery instance with mock clients."""
        return AWSAccountDiscovery(
            organizations_client=mock_org_client,
            sts_client=mock_sts_client,
        )

    def test_get_caller_identity(self, discovery, mock_sts_client):
        """Test getting caller identity."""
        result = discovery.get_caller_identity()
        assert result["Account"] == "123456789012"
        mock_sts_client.get_caller_identity.assert_called_once()

    def test_discover_accounts_returns_list(self, discovery, mock_org_client):
        """Test discovering accounts returns a list."""
        # Setup mock paginator
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {
                        "Id": "111111111111",
                        "Name": "Account 1",
                        "Status": "ACTIVE",
                        "Email": "account1@example.com",
                        "Arn": "arn:aws:organizations::111111111111:account/o-xxx/111111111111",
                    },
                    {
                        "Id": "222222222222",
                        "Name": "Account 2",
                        "Status": "ACTIVE",
                        "Email": "account2@example.com",
                        "Arn": "arn:aws:organizations::222222222222:account/o-xxx/222222222222",
                    },
                ]
            }
        ]
        mock_org_client.get_paginator.return_value = mock_paginator

        accounts = discovery.discover_accounts()

        assert len(accounts) == 2
        assert accounts[0].resource_id == "111111111111"
        assert accounts[0].display_name == "Account 1"
        assert accounts[1].resource_id == "222222222222"

    def test_discover_accounts_filters_inactive(self, discovery, mock_org_client):
        """Test that inactive accounts are filtered by default."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {"Id": "111111111111", "Name": "Active", "Status": "ACTIVE"},
                    {"Id": "222222222222", "Name": "Suspended", "Status": "SUSPENDED"},
                ]
            }
        ]
        mock_org_client.get_paginator.return_value = mock_paginator

        accounts = discovery.discover_accounts(active_only=True)

        assert len(accounts) == 1
        assert accounts[0].resource_id == "111111111111"

    def test_discover_accounts_include_patterns(self, discovery, mock_org_client):
        """Test filtering with include patterns."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {"Id": "111111111111", "Name": "prod-app", "Status": "ACTIVE"},
                    {"Id": "222222222222", "Name": "dev-app", "Status": "ACTIVE"},
                    {"Id": "333333333333", "Name": "staging-app", "Status": "ACTIVE"},
                ]
            }
        ]
        mock_org_client.get_paginator.return_value = mock_paginator

        accounts = discovery.discover_accounts(include_patterns=["prod-*"])

        assert len(accounts) == 1
        assert accounts[0].display_name == "prod-app"

    def test_discover_accounts_exclude_patterns(self, discovery, mock_org_client):
        """Test filtering with exclude patterns."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {"Id": "111111111111", "Name": "prod-app", "Status": "ACTIVE"},
                    {"Id": "222222222222", "Name": "sandbox-test", "Status": "ACTIVE"},
                ]
            }
        ]
        mock_org_client.get_paginator.return_value = mock_paginator

        accounts = discovery.discover_accounts(exclude_patterns=["sandbox-*"])

        assert len(accounts) == 1
        assert accounts[0].display_name == "prod-app"

    def test_discover_accounts_exclude_by_id(self, discovery, mock_org_client):
        """Test excluding specific account IDs."""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Accounts": [
                    {"Id": "111111111111", "Name": "Account 1", "Status": "ACTIVE"},
                    {"Id": "222222222222", "Name": "Account 2", "Status": "ACTIVE"},
                ]
            }
        ]
        mock_org_client.get_paginator.return_value = mock_paginator

        accounts = discovery.discover_accounts(exclude_accounts=["111111111111"])

        assert len(accounts) == 1
        assert accounts[0].resource_id == "222222222222"

    def test_discover_accounts_no_org_error(self, discovery, mock_org_client):
        """Test error when Organizations is not enabled."""
        mock_org_client.get_paginator.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AWSOrganizationsNotInUseException",
                    "Message": "Organizations not enabled",
                }
            },
            "ListAccounts",
        )

        with pytest.raises(DiscoveryError) as exc_info:
            discovery.discover_accounts()

        assert "not enabled" in str(exc_info.value)

    def test_discover_accounts_access_denied_error(self, discovery, mock_org_client):
        """Test error when access is denied."""
        mock_org_client.get_paginator.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            "ListAccounts",
        )

        with pytest.raises(DiscoveryError) as exc_info:
            discovery.discover_accounts()

        assert "Access denied" in str(exc_info.value)


class TestAWSAccountDiscoveryFilters:
    """Tests for filter matching logic."""

    @pytest.fixture
    def discovery(self):
        """Create discovery instance with mocked clients."""
        return AWSAccountDiscovery(
            organizations_client=MagicMock(),
            sts_client=MagicMock(),
        )

    def test_matches_filters_no_filters(self, discovery):
        """Test that all accounts match when no filters specified."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="Test Account",
            include_patterns=None,
            exclude_patterns=None,
            exclude_accounts=None,
        )
        assert result is True

    def test_matches_filters_exclude_account(self, discovery):
        """Test explicit account ID exclusion."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="Test Account",
            include_patterns=None,
            exclude_patterns=None,
            exclude_accounts=["123456789012"],
        )
        assert result is False

    def test_matches_filters_include_pattern_match(self, discovery):
        """Test include pattern matching."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="prod-web",
            include_patterns=["prod-*"],
            exclude_patterns=None,
            exclude_accounts=None,
        )
        assert result is True

    def test_matches_filters_include_pattern_no_match(self, discovery):
        """Test include pattern not matching."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="dev-web",
            include_patterns=["prod-*"],
            exclude_patterns=None,
            exclude_accounts=None,
        )
        assert result is False

    def test_matches_filters_exclude_pattern_match(self, discovery):
        """Test exclude pattern matching."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="sandbox-test",
            include_patterns=None,
            exclude_patterns=["sandbox-*"],
            exclude_accounts=None,
        )
        assert result is False

    def test_matches_filters_pattern_matches_id(self, discovery):
        """Test that patterns can match account IDs too."""
        result = discovery._matches_filters(
            account_id="123456789012",
            account_name="Some Account",
            include_patterns=["123*"],
            exclude_patterns=None,
            exclude_accounts=None,
        )
        assert result is True
