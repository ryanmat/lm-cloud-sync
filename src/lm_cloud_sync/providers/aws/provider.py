# Description: AWS provider implementation for lm-cloud-sync.
# Description: Handles AWS account discovery and LogicMonitor integration management.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lm_cloud_sync.core.exceptions import ConfigurationError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup
from lm_cloud_sync.providers.aws.auth import build_role_arn, get_external_id
from lm_cloud_sync.providers.aws.discovery import AWSAccountDiscovery
from lm_cloud_sync.providers.aws.groups import (
    create_aws_group,
    delete_aws_group,
    list_aws_groups,
)
from lm_cloud_sync.providers.base import CloudProviderBase

if TYPE_CHECKING:
    from lm_cloud_sync.core.config import AWSConfig


class AWSProvider(CloudProviderBase):
    """AWS cloud provider implementation.

    Handles discovery of AWS accounts via Organizations API and management
    of LogicMonitor AWS integrations (device groups with groupType AWS/AwsRoot).
    """

    def __init__(
        self,
        config: AWSConfig | None = None,
        role_name: str | None = None,
    ) -> None:
        """Initialize AWS provider.

        Args:
            config: AWS configuration. If None, uses defaults.
            role_name: IAM role name to assume in each account.
                      Overrides config if provided.
        """
        self._config = config
        self._role_name = role_name
        self._discovery: AWSAccountDiscovery | None = None
        self._external_id: str | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "aws"

    @property
    def provider_type(self) -> CloudProvider:
        """CloudProvider enum value."""
        return CloudProvider.AWS

    @property
    def group_type(self) -> str:
        """LogicMonitor groupType value."""
        return "AWS/AwsRoot"

    def _get_role_name(self) -> str:
        """Get IAM role name from config or override."""
        if self._role_name:
            return self._role_name
        if self._config and self._config.role_name:
            return self._config.role_name
        return "LogicMonitorRole"

    def _get_discovery(self) -> AWSAccountDiscovery:
        """Get or create AWS discovery client."""
        if self._discovery is None:
            self._discovery = AWSAccountDiscovery()
        return self._discovery

    def _get_external_id(self, client: LogicMonitorClient) -> str:
        """Get or fetch external ID from LogicMonitor."""
        if self._external_id is None:
            self._external_id = get_external_id(client)
        return self._external_id

    def discover(self, auto_discover: bool = False) -> list[CloudResource]:
        """Discover AWS accounts.

        Args:
            auto_discover: If True, uses Organizations API to discover all
                          accounts. If False, uses explicit config (not yet implemented).

        Returns:
            List of AWSAccount resources.

        Raises:
            ConfigurationError: If auto_discover is False and no accounts configured.
        """
        if not auto_discover:
            # For now, require auto_discover for AWS
            # Future: support explicit account list in config
            raise ConfigurationError(
                "AWS discovery requires --auto-discover flag. "
                "Explicit account configuration is not yet supported."
            )

        discovery = self._get_discovery()

        # Get filter settings from config
        include_patterns = None
        exclude_patterns = None
        exclude_accounts = None

        if self._config and self._config.filters:
            filters = self._config.filters
            include_patterns = filters.include_patterns or None
            exclude_patterns = filters.exclude_patterns or None
            exclude_accounts = filters.exclude_resources or None

        accounts = discovery.discover_accounts(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            exclude_accounts=exclude_accounts,
        )

        return accounts  # type: ignore[return-value]

    def list_integrations(self, client: LogicMonitorClient) -> list[LMCloudGroup]:
        """List existing AWS integrations in LogicMonitor.

        Args:
            client: LogicMonitor API client.

        Returns:
            List of LMCloudGroup objects for AWS.
        """
        return list_aws_groups(client)

    def create_integration(
        self,
        client: LogicMonitorClient,
        resource: CloudResource,
        parent_id: int = 1,
        name_template: str = "AWS - {resource_id}",
        custom_properties: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> LMCloudGroup:
        """Create an AWS integration in LogicMonitor.

        Args:
            client: LogicMonitor API client.
            resource: AWS account resource.
            parent_id: Parent group ID in LogicMonitor.
            name_template: Template for the group name.
            custom_properties: Custom properties to add.
            **kwargs: Additional options:
                - regions: List of AWS regions to monitor.
                - services: List of AWS services to monitor.
                - schedule: Cron schedule for netscans.
                - external_id: Override the external ID (optional).

        Returns:
            Created LMCloudGroup.
        """
        role_name = self._get_role_name()
        role_arn = build_role_arn(resource.resource_id, role_name)

        # Get or use provided external ID
        external_id = kwargs.get("external_id")
        if not external_id:
            external_id = self._get_external_id(client)

        # Get regions and services from config or kwargs
        regions = kwargs.get("regions")
        services = kwargs.get("services")
        schedule = kwargs.get("schedule", "0 * * * *")

        if self._config:
            if regions is None:
                regions = self._config.regions
            if services is None:
                services = self._config.services

        return create_aws_group(
            client=client,
            resource=resource,
            assumed_role_arn=role_arn,
            external_id=external_id,
            parent_id=parent_id,
            name_template=name_template,
            regions=regions,
            services=services,
            schedule=schedule,
            custom_properties=custom_properties,
        )

    def delete_integration(self, client: LogicMonitorClient, group_id: int) -> None:
        """Delete an AWS integration from LogicMonitor.

        Args:
            client: LogicMonitor API client.
            group_id: ID of the LM group to delete.
        """
        delete_aws_group(client, group_id)
