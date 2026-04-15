# Description: LogicMonitor AWS group operations.
# Description: Handles creating, listing, and deleting AWS device groups in LM.

from __future__ import annotations

import logging
from typing import Any

from lm_cloud_sync.core.exceptions import GroupExistsError, LMAPIError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import CloudProvider, CloudResource, LMCloudGroup

logger = logging.getLogger(__name__)


def list_aws_groups(client: LogicMonitorClient) -> list[LMCloudGroup]:
    """List all AWS integrations (device groups with groupType AWS/AwsRoot).

    Args:
        client: LogicMonitor API client.

    Returns:
        List of LMCloudGroup objects representing AWS integrations.
    """
    response = client.get(
        "device/groups",
        params={
            "filter": 'groupType:"AWS/AwsRoot"',
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


def get_group_by_account_id(client: LogicMonitorClient, account_id: str) -> LMCloudGroup | None:
    """Get an AWS group by its AWS account ID.

    Args:
        client: LogicMonitor API client.
        account_id: AWS account ID to find.

    Returns:
        LMCloudGroup if found, None otherwise.
    """
    groups = list_aws_groups(client)

    for group in groups:
        if group.resource_id == account_id:
            return group

    return None


def create_aws_group(
    client: LogicMonitorClient,
    resource: CloudResource,
    assumed_role_arn: str,
    external_id: str,
    parent_id: int = 1,
    name_template: str = "AWS - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> LMCloudGroup:
    """Create a new AWS integration in LogicMonitor.

    Args:
        client: LogicMonitor API client.
        resource: AWS account resource to add.
        assumed_role_arn: IAM role ARN that LogicMonitor will assume.
        external_id: External ID for cross-account role assumption.
        parent_id: Parent group ID in LM (default: 1, root).
        name_template: Template for group name.
        description: Group description.
        regions: List of AWS regions to monitor.
        services: List of AWS services to monitor.
        schedule: Cron schedule for netscans.
        custom_properties: Custom properties to add to the group.

    Returns:
        Created LMCloudGroup.

    Raises:
        GroupExistsError: If a group for this account already exists.
        LMAPIError: For other API errors.
    """
    payload = _build_aws_group_payload(
        resource=resource,
        assumed_role_arn=assumed_role_arn,
        external_id=external_id,
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
                f"AWS group for account {resource.resource_id} already exists"
            ) from e
        raise

    return LMCloudGroup(
        id=response.get("id"),
        name=response.get("name", payload["name"]),
        provider=CloudProvider.AWS,
        resource_id=resource.resource_id,
        description=response.get("description", description),
        parent_id=response.get("parentId", parent_id),
        custom_properties=custom_properties or {},
        netscan_frequency=schedule,
    )


def delete_aws_group(client: LogicMonitorClient, group_id: int) -> None:
    """Delete an AWS integration from LogicMonitor.

    Args:
        client: LogicMonitor API client.
        group_id: ID of the group to delete.
    """
    client.delete(f"device/groups/{group_id}")


def _build_aws_group_payload(
    resource: CloudResource,
    assumed_role_arn: str,
    external_id: str,
    parent_id: int = 1,
    name_template: str = "AWS - {resource_id}",
    description: str = "",
    regions: list[str] | None = None,
    services: list[str] | None = None,
    schedule: str = "0 * * * *",
    custom_properties: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the API payload for creating an AWS device group."""
    regions = regions or ["us-east-1", "us-west-2"]
    services = services or ["EC2", "RDS", "S3"]
    custom_properties = custom_properties or {}

    name = name_template.format(
        resource_id=resource.resource_id,
        display_name=resource.display_name,
        provider="AWS",
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
        "description": description or f"AWS Account: {resource.display_name}",
        "parentId": parent_id,
        "groupType": "AWS/AwsRoot",
        "customProperties": custom_props_list,
        "extra": {
            "account": {
                "assumedRoleArn": assumed_role_arn,
                "externalId": external_id,
                "collectorId": -2,  # AWS Collector
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

    # AWS groups use assumedRoleArn to identify the account
    role_arn = account.get("assumedRoleArn", "")
    if not role_arn:
        logger.warning(
            "Skipping unparseable AWS group (id=%s): missing assumedRoleArn",
            item.get("id"),
        )
        return None

    # Extract account ID from ARN: arn:aws:iam::123456789012:role/RoleName
    try:
        account_id = role_arn.split(":")[4]
    except IndexError:
        logger.warning(
            "Skipping AWS group (id=%s): malformed ARN '%s'",
            item.get("id"),
            role_arn,
        )
        return None

    custom_props = {}
    for prop in item.get("customProperties", []):
        if isinstance(prop, dict) and "name" in prop and "value" in prop:
            custom_props[prop["name"]] = prop["value"]

    return LMCloudGroup(
        id=item.get("id"),
        name=item.get("name", ""),
        provider=CloudProvider.AWS,
        resource_id=account_id,
        description=item.get("description", ""),
        parent_id=item.get("parentId", 1),
        custom_properties=custom_props,
        netscan_frequency=account.get("schedule", "0 * * * *"),
    )
