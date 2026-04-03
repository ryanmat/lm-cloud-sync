# Description: Abstract base class for cloud providers.
# Description: Defines the provider interface for AWS, Azure, and GCP implementations.

"""Abstract base class for cloud providers."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup, SyncResult

logger = logging.getLogger(__name__)


class CloudProviderBase(ABC):
    """Abstract base class for cloud provider implementations.

    Each cloud provider (AWS, Azure, GCP) must implement this interface to:
    1. Discover cloud resources (accounts, subscriptions, projects)
    2. List existing LogicMonitor integrations
    3. Create new LogicMonitor integrations
    4. Delete LogicMonitor integrations
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (aws, azure, gcp)."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> CloudProvider:
        """CloudProvider enum value."""
        pass

    @property
    @abstractmethod
    def group_type(self) -> str:
        """LogicMonitor groupType value for this provider.

        Examples:
            - AWS: "AWS/AwsRoot"
            - Azure: "Azure/AzureRoot"
            - GCP: "GCP/GcpRoot"
        """
        pass

    @abstractmethod
    def discover(self, auto_discover: bool = False) -> list[CloudResource]:
        """Discover cloud resources.

        Args:
            auto_discover: If True, use organization-level discovery APIs.
                          If False, use explicit configuration.

        Returns:
            List of discovered cloud resources.
        """
        pass

    @abstractmethod
    def list_integrations(self, client: LogicMonitorClient) -> list[LMCloudGroup]:
        """List existing LogicMonitor integrations for this provider.

        Args:
            client: LogicMonitor API client.

        Returns:
            List of LMCloudGroup objects for this provider.
        """
        pass

    @abstractmethod
    def create_integration(
        self,
        client: LogicMonitorClient,
        resource: CloudResource,
        parent_id: int = 1,
        name_template: str = "{provider} - {resource_id}",
        custom_properties: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> LMCloudGroup:
        """Create a LogicMonitor integration for a cloud resource.

        Args:
            client: LogicMonitor API client.
            resource: Cloud resource to create integration for.
            parent_id: Parent group ID in LogicMonitor.
            name_template: Template for the group name.
            custom_properties: Custom properties to add to the group.
            **kwargs: Provider-specific options.

        Returns:
            Created LMCloudGroup.
        """
        pass

    @abstractmethod
    def delete_integration(self, client: LogicMonitorClient, group_id: int) -> None:
        """Delete a LogicMonitor integration.

        Args:
            client: LogicMonitor API client.
            group_id: ID of the LM group to delete.
        """
        pass

    def sync(
        self,
        client: LogicMonitorClient,
        dry_run: bool = False,
        auto_discover: bool = False,
        create_missing: bool = True,
        delete_orphans: bool = False,
        parent_id: int = 1,
        name_template: str = "{provider} - {resource_id}",
        custom_properties: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> SyncResult:
        """Sync cloud resources to LogicMonitor.

        Args:
            client: LogicMonitor API client.
            dry_run: If True, don't make any changes.
            auto_discover: Use organization-level discovery.
            create_missing: Create integrations for new resources.
            delete_orphans: Delete integrations for removed resources.
            parent_id: Parent group ID for new integrations.
            name_template: Template for group names.
            custom_properties: Custom properties for all groups.
            **kwargs: Provider-specific options.

        Returns:
            SyncResult with details of what was done.
        """
        result = SyncResult(provider=self.provider_type, dry_run=dry_run)

        # Discover resources
        resources = self.discover(auto_discover=auto_discover)
        resource_ids = {r.resource_id for r in resources}

        # Get existing integrations
        existing = self.list_integrations(client)
        existing_by_id = {g.resource_id: g for g in existing}

        # Create missing integrations
        if create_missing:
            for resource in resources:
                if resource.resource_id not in existing_by_id:
                    if dry_run:
                        result.created.append(resource.resource_id)
                    else:
                        try:
                            self.create_integration(
                                client=client,
                                resource=resource,
                                parent_id=parent_id,
                                name_template=name_template,
                                custom_properties=custom_properties,
                                **kwargs,
                            )
                            result.created.append(resource.resource_id)
                        except Exception as e:
                            logger.exception(
                                "Failed to create integration for %s",
                                resource.resource_id,
                            )
                            result.failed[resource.resource_id] = str(e)
                else:
                    result.skipped.append(resource.resource_id)

        # Delete orphans
        if delete_orphans:
            for group in existing:
                if group.resource_id not in resource_ids:
                    if dry_run:
                        result.deleted.append(group.resource_id)
                    else:
                        try:
                            if group.id is not None:
                                self.delete_integration(client, group.id)
                            result.deleted.append(group.resource_id)
                        except Exception as e:
                            logger.exception(
                                "Failed to delete integration for %s",
                                group.resource_id,
                            )
                            result.failed[group.resource_id] = str(e)

        return result

    def _format_group_name(
        self, template: str, resource: CloudResource
    ) -> str:
        """Format a group name using the template.

        Args:
            template: Name template with placeholders.
            resource: Cloud resource.

        Returns:
            Formatted group name.
        """
        return template.format(
            provider=self.name.upper(),
            resource_id=resource.resource_id,
            display_name=resource.display_name,
        )
