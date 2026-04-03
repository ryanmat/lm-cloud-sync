# Description: GCP provider implementation for lm-cloud-sync.
# Description: Handles GCP project discovery and LogicMonitor integration management.

"""GCP provider implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lm_cloud_sync.core.exceptions import ConfigurationError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup
from lm_cloud_sync.providers.base import CloudProviderBase
from lm_cloud_sync.providers.gcp.discovery import GCPProjectDiscovery
from lm_cloud_sync.providers.gcp.groups import (
    create_gcp_group,
    delete_gcp_group,
    list_gcp_groups,
)

if TYPE_CHECKING:
    from lm_cloud_sync.core.config import GCPConfig


class GCPProvider(CloudProviderBase):
    """GCP cloud provider implementation.

    Handles discovery of GCP projects and management of LogicMonitor
    GCP integrations (device groups with groupType GCP/GcpRoot).
    """

    def __init__(
        self,
        config: GCPConfig | None = None,
        service_account_key_path: Path | str | None = None,
    ) -> None:
        """Initialize GCP provider.

        Args:
            config: GCP configuration. If None, uses defaults.
            service_account_key_path: Path to service account JSON key.
                                     Overrides config if provided.
        """
        self._config = config
        self._sa_key_path = (
            Path(service_account_key_path) if service_account_key_path else None
        )
        self._discovery: GCPProjectDiscovery | None = None
        self._service_account_key: dict | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "gcp"

    @property
    def provider_type(self) -> CloudProvider:
        """CloudProvider enum value."""
        return CloudProvider.GCP

    @property
    def group_type(self) -> str:
        """LogicMonitor groupType value."""
        return "GCP/GcpRoot"

    def _get_sa_key_path(self) -> Path | None:
        """Get service account key path from config or override."""
        if self._sa_key_path:
            return self._sa_key_path
        if self._config and self._config.service_account_key_path:
            return self._config.service_account_key_path
        return None

    def _get_discovery(self) -> GCPProjectDiscovery:
        """Get or create GCP discovery client."""
        if self._discovery is None:
            key_path = self._get_sa_key_path()
            if key_path:
                self._discovery = GCPProjectDiscovery.from_service_account_file(key_path)
            else:
                # Use application default credentials
                self._discovery = GCPProjectDiscovery()
        return self._discovery

    def _get_service_account_key(self) -> dict:
        """Load service account key for LM integration."""
        if self._service_account_key is None:
            key_path = self._get_sa_key_path()
            if key_path and key_path.exists():
                self._service_account_key = json.loads(key_path.read_text())
            else:
                raise ConfigurationError(
                    "Service account key required for creating LM integrations. "
                    "Set GCP_SA_KEY_PATH or GOOGLE_APPLICATION_CREDENTIALS."
                )
        return self._service_account_key

    def discover(self, auto_discover: bool = False) -> list[CloudResource]:
        """Discover GCP projects.

        Args:
            auto_discover: If True, uses Resource Manager API to discover all
                          accessible projects. If False, uses explicit config.

        Returns:
            List of GCPProject resources.
        """
        discovery = self._get_discovery()

        # Get filter settings from config
        include_patterns = None
        exclude_patterns = None
        exclude_projects = None
        required_labels = None
        excluded_labels = None

        if self._config and self._config.filters:
            filters = self._config.filters
            include_patterns = filters.include_patterns or None
            exclude_patterns = filters.exclude_patterns or None
            exclude_projects = filters.exclude_resources or None
            required_labels = filters.required_tags or None
            excluded_labels = filters.excluded_tags or None

        projects = discovery.discover_projects(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            exclude_projects=exclude_projects,
            required_labels=required_labels,
            excluded_labels=excluded_labels,
        )

        return projects  # type: ignore[return-value]

    def list_integrations(self, client: LogicMonitorClient) -> list[LMCloudGroup]:
        """List existing GCP integrations in LogicMonitor.

        Args:
            client: LogicMonitor API client.

        Returns:
            List of LMCloudGroup objects for GCP.
        """
        return list_gcp_groups(client)

    def create_integration(
        self,
        client: LogicMonitorClient,
        resource: CloudResource,
        parent_id: int = 1,
        name_template: str = "GCP - {resource_id}",
        custom_properties: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> LMCloudGroup:
        """Create a GCP integration in LogicMonitor.

        Args:
            client: LogicMonitor API client.
            resource: GCP project resource.
            parent_id: Parent group ID in LogicMonitor.
            name_template: Template for the group name.
            custom_properties: Custom properties to add.
            **kwargs: Additional options:
                - regions: List of GCP regions to monitor.
                - services: List of GCP services to monitor.
                - schedule: Cron schedule for netscans.

        Returns:
            Created LMCloudGroup.
        """
        sa_key = self._get_service_account_key()

        # Get regions and services from config or kwargs
        regions = kwargs.get("regions")
        services = kwargs.get("services")
        schedule = kwargs.get("schedule", "0 * * * *")

        if self._config:
            if regions is None:
                regions = self._config.regions
            if services is None:
                services = self._config.services

        return create_gcp_group(
            client=client,
            resource=resource,
            service_account_key=sa_key,
            parent_id=parent_id,
            name_template=name_template,
            regions=regions,
            services=services,
            schedule=schedule,
            custom_properties=custom_properties,
        )

    def delete_integration(self, client: LogicMonitorClient, group_id: int) -> None:
        """Delete a GCP integration from LogicMonitor.

        Args:
            client: LogicMonitor API client.
            group_id: ID of the LM group to delete.
        """
        delete_gcp_group(client, group_id)
