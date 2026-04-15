# Description: LogicMonitor Azure group operations.
# Description: Handles creating, listing, and deleting Azure device groups in LM.

from __future__ import annotations

import logging
from typing import Any

from lm_cloud_sync.core.exceptions import GroupExistsError, LMAPIError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup

logger = logging.getLogger(__name__)


def list_azure_groups(client: LogicMonitorClient) -> list[LMCloudGroup]:
    """List all Azure integrations (device groups with groupType Azure/AzureRoot).

    Args:
        client: LogicMonitor API client.

    Returns:
        List of LMCloudGroup objects representing Azure integrations.
    """
    response = client.get(
        "device/groups",
        params={
            "filter": 'groupType:"Azure/AzureRoot"',
            "size": 1000,
            "fields": "id,name,description,parentId,groupType,customProperties,extra",
        },
    )

    groups = []
    data = response.get("data", response)
    items = data.get("items", []) if isinstance(data, dict) else []
    for item in items:
        group = _parse_group_response(item)
        if group:
            groups.append(group)

    return groups


def get_group_by_subscription_id(
    client: LogicMonitorClient, subscription_id: str
) -> LMCloudGroup | None:
    """Get an Azure group by its subscription ID.

    Args:
        client: LogicMonitor API client.
        subscription_id: Azure subscription ID to find.

    Returns:
        LMCloudGroup if found, None otherwise.
    """
    groups = list_azure_groups(client)

    for group in groups:
        if group.resource_id == subscription_id:
            return group

    return None


def create_azure_group(
    client: LogicMonitorClient,
    resource: CloudResource,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    parent_id: int = 1,
    name_template: str = "Azure - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> LMCloudGroup:
    """Create a new Azure integration in LogicMonitor.

    Args:
        client: LogicMonitor API client.
        resource: Azure subscription resource to add.
        tenant_id: Azure AD tenant ID.
        client_id: Service Principal client/application ID.
        client_secret: Service Principal secret.
        parent_id: Parent group ID in LM (default: 1, root).
        name_template: Template for group name.
        description: Group description.
        regions: List of Azure regions to monitor.
        services: List of Azure services to monitor.
        schedule: Cron schedule for netscans.
        custom_properties: Custom properties to add to the group.

    Returns:
        Created LMCloudGroup.

    Raises:
        GroupExistsError: If a group for this subscription already exists.
        LMAPIError: For other API errors.
    """
    payload = _build_azure_group_payload(
        resource=resource,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        parent_id=parent_id,
        name_template=name_template,
        description=description,
        regions=regions,
        services=services,
        schedule=schedule,
        custom_properties=custom_properties,
    )

    try:
        response = client.post("device/groups", json=payload)
    except LMAPIError as e:
        if "already exists" in str(e).lower():
            raise GroupExistsError(
                f"Azure group for subscription {resource.resource_id} already exists"
            ) from e
        raise

    return LMCloudGroup(
        id=response.get("id"),
        name=response.get("name", payload["name"]),
        provider=CloudProvider.AZURE,
        resource_id=resource.resource_id,
        description=response.get("description", description),
        parent_id=response.get("parentId", parent_id),
        custom_properties=custom_properties or {},
        netscan_frequency=schedule,
    )


def delete_azure_group(client: LogicMonitorClient, group_id: int) -> None:
    """Delete an Azure integration from LogicMonitor.

    Args:
        client: LogicMonitor API client.
        group_id: ID of the group to delete.
    """
    client.delete(f"device/groups/{group_id}")


def _build_azure_group_payload(
    resource: CloudResource,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    parent_id: int = 1,
    name_template: str = "Azure - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the API payload for creating an Azure device group."""
    regions = regions or ["eastus", "westus2"]
    # Enable all Azure services by default for comprehensive monitoring
    services = services or [
        "APIMANAGEMENT",
        "APPLICATIONGATEWAY",
        "APPSERVICE",
        "AUTOMATIONACCOUNT",
        "BATCHACCOUNT",
        "CDNPROFILE",
        "COGNITIVESERVICES",
        "CONTAINERINSTANCE",
        "CONTAINERREGISTRY",
        "COSMOSDB",
        "DATABRICKS",
        "DATAFACTORY",
        "DATALAKEANALYTICS",
        "DATALAKESTORE",
        "EVENTGRID",
        "EVENTHUB",
        "EXPRESSROUTE",
        "FIREWALL",
        "FRONTDOOR",
        "FUNCTIONS",
        "HDINSIGHT",
        "IOTHUB",
        "KEYVAULT",
        "KUSTO",
        "LOADBALANCER",
        "LOGICAPPS",
        "MARIADB",
        "MYSQL",
        "NOTIFICATIONHUB",
        "POSTGRESQL",
        "REDISCACHE",
        "SEARCHSERVICE",
        "SERVICEBUS",
        "SIGNALR",
        "SQLDATABASE",
        "SQLMANAGEDINSTANCE",
        "STORAGEACCOUNT",
        "STREAMANALYTICS",
        "SYNAPSE",
        "VIRTUALMACHINE",
        "VIRTUALMACHINESCALESET",
        "VPNGATEWAY",
    ]
    custom_properties = custom_properties or {}

    name = name_template.format(
        resource_id=resource.resource_id,
        display_name=resource.display_name,
        provider="Azure",
    )

    default_service_config = {
        "useDefault": True,
        "selectAll": False,
        "monitoringRegions": regions,
        "tags": [],
        "nameFilter": [],
        "deadOperation": "KEEP_7_DAYS",
        "disableTerminatedHostAlerting": True,
    }

    services_config = {}
    for service in services:
        services_config[service] = {
            "useDefault": True,
            "selectAll": False,
            "monitoringRegions": regions,
            "tags": [],
            "nameFilter": [],
            "deadOperation": "KEEP_7_DAYS",
            "disableTerminatedHostAlerting": True,
        }

    custom_props_list = [{"name": k, "value": v} for k, v in custom_properties.items()]

    payload: dict[str, Any] = {
        "name": name,
        "description": description or f"Azure Subscription: {resource.display_name}",
        "parentId": parent_id,
        "groupType": "Azure/AzureRoot",
        "customProperties": custom_props_list,
        "extra": {
            "account": {
                "tenantId": tenant_id,
                "clientId": client_id,
                "secretKey": client_secret,
                "subscriptionIds": resource.resource_id,
                "collectorId": -4,  # Azure Collector
                "schedule": schedule,
            },
            "default": default_service_config,
            "services": services_config,
        },
    }

    return payload


def _parse_group_response(item: dict[str, Any]) -> LMCloudGroup | None:
    """Parse an API response item into an LMCloudGroup."""
    extra = item.get("extra", {})
    account = extra.get("account", {})

    # Azure groups use subscriptionIds to identify the subscription
    subscription_ids = account.get("subscriptionIds", "")
    if not subscription_ids:
        logger.warning(
            "Skipping unparseable Azure group (id=%s): missing subscriptionIds",
            item.get("id"),
        )
        return None

    # subscriptionIds can be comma-separated, take the first one
    subscription_id = subscription_ids.split(",")[0].strip()

    custom_props = {}
    for prop in item.get("customProperties", []):
        if isinstance(prop, dict) and "name" in prop and "value" in prop:
            custom_props[prop["name"]] = prop["value"]

    return LMCloudGroup(
        id=item.get("id"),
        name=item.get("name", ""),
        provider=CloudProvider.AZURE,
        resource_id=subscription_id,
        description=item.get("description", ""),
        parent_id=item.get("parentId", 1),
        custom_properties=custom_props,
        netscan_frequency=account.get("schedule", "0 * * * *"),
    )
