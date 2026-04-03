# Description: Azure subscription discovery using Management API.
# Description: Discovers Azure subscriptions for LogicMonitor integration.

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.subscription import SubscriptionClient

from lm_cloud_sync.core.exceptions import DiscoveryError
from lm_cloud_sync.core.models import AzureSubscription

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

logger = logging.getLogger(__name__)


class AzureSubscriptionDiscovery:
    """Discovers Azure subscriptions using the Subscription Management API.

    Requires permissions:
    - Reader role at the tenant or management group level
    """

    def __init__(
        self,
        credential: TokenCredential | None = None,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Azure subscription discovery.

        Args:
            credential: Azure credential. If None, uses DefaultAzureCredential
                       or creates from tenant_id/client_id/client_secret.
            tenant_id: Azure AD tenant ID for Service Principal auth.
            client_id: Service Principal client/application ID.
            client_secret: Service Principal secret.
        """
        self._credential = credential
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._subscription_client: SubscriptionClient | None = None

    @property
    def credential(self) -> TokenCredential:
        """Get or create Azure credential."""
        if self._credential is None:
            if self._tenant_id and self._client_id and self._client_secret:
                self._credential = ClientSecretCredential(
                    tenant_id=self._tenant_id,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )
            else:
                # Use default credential chain (env vars, managed identity, CLI, etc.)
                self._credential = DefaultAzureCredential()
        return self._credential

    @property
    def subscription_client(self) -> SubscriptionClient:
        """Get or create Subscription client."""
        if self._subscription_client is None:
            self._subscription_client = SubscriptionClient(self.credential)
        return self._subscription_client

    def discover_subscriptions(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        exclude_subscriptions: list[str] | None = None,
        enabled_only: bool = True,
    ) -> list[AzureSubscription]:
        """Discover Azure subscriptions.

        Args:
            include_patterns: Glob patterns for subscription names to include.
            exclude_patterns: Glob patterns for subscription names to exclude.
            exclude_subscriptions: Specific subscription IDs to exclude.
            enabled_only: Only return Enabled subscriptions (default True).

        Returns:
            List of AzureSubscription objects.

        Raises:
            DiscoveryError: If subscription discovery fails.
        """
        try:
            subscriptions = self._list_all_subscriptions()
        except ClientAuthenticationError as e:
            raise DiscoveryError(
                "Azure authentication failed. Check your credentials. "
                f"Error: {e}"
            ) from e
        except HttpResponseError as e:
            raise DiscoveryError(f"Azure API error: {e}") from e
        except Exception as e:
            raise DiscoveryError(f"Failed to list Azure subscriptions: {e}") from e

        # Filter subscriptions
        filtered = []
        for sub in subscriptions:
            if enabled_only and sub.status != "Enabled":
                continue

            if not self._matches_filters(
                subscription_id=sub.resource_id,
                subscription_name=sub.display_name,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                exclude_subscriptions=exclude_subscriptions,
            ):
                continue

            filtered.append(sub)

        logger.info(
            f"Discovered {len(filtered)} Azure subscriptions (filtered from {len(subscriptions)})"
        )
        return filtered

    def _list_all_subscriptions(self) -> list[AzureSubscription]:
        """List all subscriptions accessible to the credential."""
        subscriptions = []

        for sub in self.subscription_client.subscriptions.list():
            # Handle state as either enum or string (SDK version dependent)
            if sub.state is None:
                state = "Unknown"
            elif isinstance(sub.state, str):
                state = sub.state
            else:
                state = sub.state.value

            # Handle subscription_policies safely
            policies = {}
            if sub.subscription_policies:
                if hasattr(sub.subscription_policies, "as_dict"):
                    policies = sub.subscription_policies.as_dict()
                elif isinstance(sub.subscription_policies, dict):
                    policies = sub.subscription_policies

            subscription = AzureSubscription(
                resource_id=sub.subscription_id,
                display_name=sub.display_name or sub.subscription_id,
                status=state,
                tenant_id=self._tenant_id or "",
                metadata={"subscription_policies": policies},
            )
            subscriptions.append(subscription)

        return subscriptions

    def _matches_filters(
        self,
        subscription_id: str,
        subscription_name: str,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        exclude_subscriptions: list[str] | None,
    ) -> bool:
        """Check if a subscription matches the filter criteria."""
        # Explicit exclusion by subscription ID
        if exclude_subscriptions and subscription_id in exclude_subscriptions:
            return False

        # Check include patterns (if specified, must match at least one)
        if include_patterns and not any(
            fnmatch.fnmatch(subscription_name, p)
            or fnmatch.fnmatch(subscription_id, p)
            for p in include_patterns
        ):
            return False

        # Check exclude patterns
        return not (exclude_patterns and any(fnmatch.fnmatch(subscription_name, p) or fnmatch.fnmatch(subscription_id, p) for p in exclude_patterns))
