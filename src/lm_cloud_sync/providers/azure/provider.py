# Description: Azure provider implementation for lm-cloud-sync.
# Description: Handles Azure subscription discovery and LogicMonitor integration management.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lm_cloud_sync.core.exceptions import ConfigurationError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup
from lm_cloud_sync.providers.azure.discovery import AzureSubscriptionDiscovery
from lm_cloud_sync.providers.azure.groups import (
    create_azure_group,
    delete_azure_group,
    list_azure_groups,
)
from lm_cloud_sync.providers.base import CloudProviderBase

if TYPE_CHECKING:
    from lm_cloud_sync.core.config import AzureConfig

logger = logging.getLogger(__name__)


class AzureProvider(CloudProviderBase):
    """Azure cloud provider implementation.

    Handles discovery of Azure subscriptions and management of LogicMonitor
    Azure integrations (device groups with groupType Azure/AzureRoot).
    """

    def __init__(
        self,
        config: AzureConfig | None = None,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Azure provider.

        Args:
            config: Azure configuration. If None, uses defaults.
            tenant_id: Azure AD tenant ID. Overrides config if provided.
            client_id: Service Principal client ID. Overrides config if provided.
            client_secret: Service Principal secret. Overrides config if provided.
        """
        self._config = config
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._discovery: AzureSubscriptionDiscovery | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "azure"

    @property
    def provider_type(self) -> CloudProvider:
        """CloudProvider enum value."""
        return CloudProvider.AZURE

    @property
    def group_type(self) -> str:
        """LogicMonitor groupType value."""
        return "Azure/AzureRoot"

    def _get_credentials(self) -> tuple[str, str, str]:
        """Get Azure credentials from config or overrides.

        Returns:
            Tuple of (tenant_id, client_id, client_secret).

        Raises:
            ConfigurationError: If credentials are not available.
        """
        tenant_id = self._tenant_id
        client_id = self._client_id
        client_secret = self._client_secret

        if self._config:
            if not tenant_id:
                tenant_id = self._config.tenant_id
            if not client_id:
                client_id = self._config.client_id
            if not client_secret and self._config.client_secret:
                client_secret = self._config.client_secret.get_secret_value()

        if not tenant_id or not client_id or not client_secret:
            raise ConfigurationError(
                "Azure credentials required. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, "
                "and AZURE_CLIENT_SECRET environment variables or configure in YAML."
            )

        return tenant_id, client_id, client_secret

    def _get_discovery(self) -> AzureSubscriptionDiscovery:
        """Get or create Azure discovery client."""
        if self._discovery is None:
            try:
                tenant_id, client_id, client_secret = self._get_credentials()
                self._discovery = AzureSubscriptionDiscovery(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            except ConfigurationError:
                has_partial = any([
                    self._config and self._config.tenant_id,
                    self._config and self._config.client_id,
                    self._config and self._config.client_secret,
                    self._tenant_id,
                    self._client_id,
                    self._client_secret,
                ])
                if has_partial:
                    raise
                logger.info("No explicit Azure credentials, using DefaultAzureCredential")
                self._discovery = AzureSubscriptionDiscovery()
        return self._discovery

    def discover(self, auto_discover: bool = False) -> list[CloudResource]:
        """Discover Azure subscriptions.

        Args:
            auto_discover: If True, discovers all accessible subscriptions.
                          If False, uses explicit config (not yet implemented).

        Returns:
            List of AzureSubscription resources.

        Raises:
            ConfigurationError: If auto_discover is False and no subscriptions configured.
        """
        if not auto_discover:
            raise ConfigurationError(
                "Azure discovery requires --auto-discover flag. "
                "Explicit subscription configuration is not yet supported."
            )

        discovery = self._get_discovery()

        # Get filter settings from config
        include_patterns = None
        exclude_patterns = None
        exclude_subscriptions = None

        if self._config and self._config.filters:
            filters = self._config.filters
            include_patterns = filters.include_patterns or None
            exclude_patterns = filters.exclude_patterns or None
            exclude_subscriptions = filters.exclude_resources or None

        subscriptions = discovery.discover_subscriptions(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            exclude_subscriptions=exclude_subscriptions,
        )

        return subscriptions  # type: ignore[return-value]

    def list_integrations(self, client: LogicMonitorClient) -> list[LMCloudGroup]:
        """List existing Azure integrations in LogicMonitor.

        Args:
            client: LogicMonitor API client.

        Returns:
            List of LMCloudGroup objects for Azure.
        """
        return list_azure_groups(client)

    def create_integration(
        self,
        client: LogicMonitorClient,
        resource: CloudResource,
        parent_id: int = 1,
        name_template: str = "Azure - {resource_id}",
        custom_properties: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> LMCloudGroup:
        """Create an Azure integration in LogicMonitor.

        Args:
            client: LogicMonitor API client.
            resource: Azure subscription resource.
            parent_id: Parent group ID in LogicMonitor.
            name_template: Template for the group name.
            custom_properties: Custom properties to add.
            **kwargs: Additional options:
                - regions: List of Azure regions to monitor.
                - services: List of Azure services to monitor.
                - schedule: Cron schedule for netscans.

        Returns:
            Created LMCloudGroup.
        """
        tenant_id, client_id, client_secret = self._get_credentials()

        # Get regions and services from config or kwargs
        regions = kwargs.get("regions")
        services = kwargs.get("services")
        schedule = kwargs.get("schedule", "0 * * * *")

        if self._config:
            if regions is None:
                regions = self._config.regions
            if services is None:
                services = self._config.services

        return create_azure_group(
            client=client,
            resource=resource,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            parent_id=parent_id,
            name_template=name_template,
            regions=regions,
            services=services,
            schedule=schedule,
            custom_properties=custom_properties,
        )

    def delete_integration(self, client: LogicMonitorClient, group_id: int) -> None:
        """Delete an Azure integration from LogicMonitor.

        Args:
            client: LogicMonitor API client.
            group_id: ID of the LM group to delete.
        """
        delete_azure_group(client, group_id)
