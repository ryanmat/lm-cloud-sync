# Description: LogicMonitor GCP group operations.
# Description: Handles creating, listing, and deleting GCP device groups in LM.

"""LogicMonitor GCP group operations."""

import logging
from typing import Any

from lm_cloud_sync.core.exceptions import GroupExistsError, LMAPIError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup

logger = logging.getLogger(__name__)


def list_gcp_groups(client: LogicMonitorClient) -> list[LMCloudGroup]:
    """List all GCP integrations (device groups with groupType GCP/GcpRoot).

    Args:
        client: LogicMonitor API client.

    Returns:
        List of LMCloudGroup objects representing GCP integrations.
    """
    response = client.get(
        "device/groups",
        params={
            "filter": 'groupType:"GCP/GcpRoot"',
            "size": 1000,
            "fields": "id,name,description,parentId,groupType,customProperties,extra",
        },
    )

    groups = []
    for item in response.get("items", []):
        group = _parse_group_response(item)
        if group:
            groups.append(group)

    return groups


def get_group_by_project_id(client: LogicMonitorClient, project_id: str) -> LMCloudGroup | None:
    """Get a GCP group by its GCP project ID.

    Args:
        client: LogicMonitor API client.
        project_id: GCP project ID to find.

    Returns:
        LMCloudGroup if found, None otherwise.
    """
    groups = list_gcp_groups(client)

    for group in groups:
        if group.resource_id == project_id:
            return group

    return None


def create_gcp_group(
    client: LogicMonitorClient,
    resource: CloudResource,
    service_account_key: dict[str, Any],
    parent_id: int = 1,
    name_template: str = "GCP - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> LMCloudGroup:
    """Create a new GCP integration in LogicMonitor.

    Args:
        client: LogicMonitor API client.
        resource: GCP project resource to add.
        service_account_key: GCP service account key JSON.
        parent_id: Parent group ID in LM (default: 1, root).
        name_template: Template for group name.
        description: Group description.
        regions: List of GCP regions to monitor.
        services: List of GCP services to monitor.
        schedule: Cron schedule for netscans.
        custom_properties: Custom properties to add to the group.

    Returns:
        Created LMCloudGroup.

    Raises:
        GroupExistsError: If a group for this project already exists.
        LMAPIError: For other API errors.
    """
    payload = _build_gcp_group_payload(
        resource=resource,
        service_account_key=service_account_key,
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
        # Check if the group was actually created despite the error
        # LM API returns 400 with errorDetail containing the created group
        # when there are warnings (e.g., GCP API not enabled)
        if hasattr(e, "response") and isinstance(e.response, dict):
            error_detail = e.response.get("errorDetail", {})
            if isinstance(error_detail, dict) and error_detail.get("id"):
                response = error_detail
            elif "already exists" in str(e).lower():
                raise GroupExistsError(
                    f"GCP group for project {resource.resource_id} already exists"
                ) from e
            else:
                raise
        else:
            raise

    return LMCloudGroup(
        id=response.get("id"),
        name=response.get("name", payload["name"]),
        provider=CloudProvider.GCP,
        resource_id=resource.resource_id,
        description=response.get("description", description),
        parent_id=response.get("parentId", parent_id),
        custom_properties=custom_properties or {},
        netscan_frequency=schedule,
    )


def delete_gcp_group(client: LogicMonitorClient, group_id: int) -> None:
    """Delete a GCP integration from LogicMonitor.

    Args:
        client: LogicMonitor API client.
        group_id: ID of the group to delete.
    """
    client.delete(f"device/groups/{group_id}")


def _build_gcp_group_payload(
    resource: CloudResource,
    service_account_key: dict[str, Any],
    parent_id: int = 1,
    name_template: str = "GCP - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the API payload for creating a GCP device group."""
    regions = regions or ["us-central1", "us-east1"]
    # Enable all GCP services by default for comprehensive monitoring
    services = services or [
        "APPENGINE",
        "BIGQUERY",
        "BIGTABLE",
        "CLOUDFUNCTION",
        "CLOUDRUN",
        "CLOUDSQL",
        "CLOUDTASKS",
        "COMPOSER",
        "COMPUTEENGINE",
        "DATAFLOW",
        "DATAPROC",
        "FILESTORE",
        "FIRESTORE",
        "GKE",
        "INTERCONNECT",
        "LOADBALANCING",
        "PUBSUB",
        "REDIS",
        "SPANNER",
        "STORAGE",
        "VPN",
    ]
    custom_properties = custom_properties or {}

    name = name_template.format(
        resource_id=resource.resource_id,
        display_name=resource.display_name,
        provider="GCP",
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
        "description": description,
        "parentId": parent_id,
        "groupType": "GCP/GcpRoot",
        "customProperties": custom_props_list,
        "extra": {
            "account": {
                "projectId": resource.resource_id,
                "collectorId": -2,
                "schedule": schedule,
                "serviceAccountKey": service_account_key,
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
    project_id = account.get("projectId")

    if not project_id:
        logger.warning(
            "Skipping unparseable GCP group (id=%s): missing projectId",
            item.get("id"),
        )
        return None

    custom_props = {}
    for prop in item.get("customProperties", []):
        if isinstance(prop, dict) and "name" in prop and "value" in prop:
            custom_props[prop["name"]] = prop["value"]

    return LMCloudGroup(
        id=item.get("id"),
        name=item.get("name", ""),
        provider=CloudProvider.GCP,
        resource_id=project_id,
        description=item.get("description", ""),
        parent_id=item.get("parentId", 1),
        custom_properties=custom_props,
        netscan_frequency=account.get("schedule", "0 * * * *"),
    )
