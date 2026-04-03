# Unit tests for Azure subscription discovery.

from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ClientAuthenticationError

from lm_cloud_sync.core.exceptions import DiscoveryError
from lm_cloud_sync.providers.azure.discovery import AzureSubscriptionDiscovery


class MockSubscription:
    """Mock Azure subscription object."""

    def __init__(
        self,
        subscription_id: str,
        display_name: str,
        state: str = "Enabled",
        tenant_id: str = "tenant-123",
    ):
        self.subscription_id = subscription_id
        self.display_name = display_name
        self.state = MagicMock()
        self.state.value = state
        self.tenant_id = tenant_id
        self.subscription_policies = None


class TestAzureSubscriptionDiscovery:
    """Tests for Azure subscription discovery."""

    @pytest.fixture
    def mock_credential(self):
        """Create a mock credential."""
        return MagicMock()

    @pytest.fixture
    def mock_subscription_client(self):
        """Create a mock SubscriptionClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def discovery(self, mock_credential, mock_subscription_client):
        """Create a discovery instance with mock clients."""
        disc = AzureSubscriptionDiscovery(credential=mock_credential)
        disc._subscription_client = mock_subscription_client
        return disc

    def test_discover_subscriptions_returns_list(self, discovery, mock_subscription_client):
        """Test discovering subscriptions returns a list."""
        mock_subscription_client.subscriptions.list.return_value = [
            MockSubscription("sub-1", "Subscription 1"),
            MockSubscription("sub-2", "Subscription 2"),
        ]

        subscriptions = discovery.discover_subscriptions()

        assert len(subscriptions) == 2
        assert subscriptions[0].resource_id == "sub-1"
        assert subscriptions[0].display_name == "Subscription 1"
        assert subscriptions[1].resource_id == "sub-2"

    def test_discover_subscriptions_filters_disabled(self, discovery, mock_subscription_client):
        """Test that disabled subscriptions are filtered by default."""
        mock_subscription_client.subscriptions.list.return_value = [
            MockSubscription("sub-1", "Enabled Sub", "Enabled"),
            MockSubscription("sub-2", "Disabled Sub", "Disabled"),
        ]

        subscriptions = discovery.discover_subscriptions(enabled_only=True)

        assert len(subscriptions) == 1
        assert subscriptions[0].resource_id == "sub-1"

    def test_discover_subscriptions_include_patterns(self, discovery, mock_subscription_client):
        """Test filtering with include patterns."""
        mock_subscription_client.subscriptions.list.return_value = [
            MockSubscription("sub-1", "prod-app"),
            MockSubscription("sub-2", "dev-app"),
            MockSubscription("sub-3", "staging-app"),
        ]

        subscriptions = discovery.discover_subscriptions(include_patterns=["prod-*"])

        assert len(subscriptions) == 1
        assert subscriptions[0].display_name == "prod-app"

    def test_discover_subscriptions_exclude_patterns(self, discovery, mock_subscription_client):
        """Test filtering with exclude patterns."""
        mock_subscription_client.subscriptions.list.return_value = [
            MockSubscription("sub-1", "prod-app"),
            MockSubscription("sub-2", "sandbox-test"),
        ]

        subscriptions = discovery.discover_subscriptions(exclude_patterns=["sandbox-*"])

        assert len(subscriptions) == 1
        assert subscriptions[0].display_name == "prod-app"

    def test_discover_subscriptions_exclude_by_id(self, discovery, mock_subscription_client):
        """Test excluding specific subscription IDs."""
        mock_subscription_client.subscriptions.list.return_value = [
            MockSubscription("sub-1", "Subscription 1"),
            MockSubscription("sub-2", "Subscription 2"),
        ]

        subscriptions = discovery.discover_subscriptions(exclude_subscriptions=["sub-1"])

        assert len(subscriptions) == 1
        assert subscriptions[0].resource_id == "sub-2"

    def test_discover_subscriptions_auth_error(self, discovery, mock_subscription_client):
        """Test error when authentication fails."""
        mock_subscription_client.subscriptions.list.side_effect = ClientAuthenticationError(
            "Authentication failed"
        )

        with pytest.raises(DiscoveryError) as exc_info:
            discovery.discover_subscriptions()

        assert "authentication failed" in str(exc_info.value).lower()


class TestAzureSubscriptionDiscoveryFilters:
    """Tests for filter matching logic."""

    @pytest.fixture
    def discovery(self):
        """Create discovery instance with mocked clients."""
        return AzureSubscriptionDiscovery(credential=MagicMock())

    def test_matches_filters_no_filters(self, discovery):
        """Test that all subscriptions match when no filters specified."""
        result = discovery._matches_filters(
            subscription_id="sub-123",
            subscription_name="Test Subscription",
            include_patterns=None,
            exclude_patterns=None,
            exclude_subscriptions=None,
        )
        assert result is True

    def test_matches_filters_exclude_subscription(self, discovery):
        """Test explicit subscription ID exclusion."""
        result = discovery._matches_filters(
            subscription_id="sub-123",
            subscription_name="Test Subscription",
            include_patterns=None,
            exclude_patterns=None,
            exclude_subscriptions=["sub-123"],
        )
        assert result is False

    def test_matches_filters_include_pattern_match(self, discovery):
        """Test include pattern matching."""
        result = discovery._matches_filters(
            subscription_id="sub-123",
            subscription_name="prod-web",
            include_patterns=["prod-*"],
            exclude_patterns=None,
            exclude_subscriptions=None,
        )
        assert result is True

    def test_matches_filters_include_pattern_no_match(self, discovery):
        """Test include pattern not matching."""
        result = discovery._matches_filters(
            subscription_id="sub-123",
            subscription_name="dev-web",
            include_patterns=["prod-*"],
            exclude_patterns=None,
            exclude_subscriptions=None,
        )
        assert result is False

    def test_matches_filters_exclude_pattern_match(self, discovery):
        """Test exclude pattern matching."""
        result = discovery._matches_filters(
            subscription_id="sub-123",
            subscription_name="sandbox-test",
            include_patterns=None,
            exclude_patterns=["sandbox-*"],
            exclude_subscriptions=None,
        )
        assert result is False
