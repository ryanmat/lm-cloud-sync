# Description: Core resync logic for triggering LM cloud sync engine.
# Description: Performs GET-modify-PUT on cloud root groups to trigger credential validation and rediscovery.

"""Core resync logic for triggering LM cloud sync engine.

A full PUT on /device/groups/{id} for cloud root groups (groupType:
AWS/AwsRoot, Azure/AzureRoot, GCP/GcpRoot) triggers the sync engine:
credential validation, region re-evaluation, and service re-discovery.
PATCH or partial PUT does NOT trigger this sync.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from lm_cloud_sync.core.exceptions import LMAPIError
from lm_cloud_sync.core.lm_client import LogicMonitorClient
from lm_cloud_sync.core.models import ResyncResult

logger = logging.getLogger(__name__)

CLOUD_GROUP_TYPES: dict[str, str] = {
    "aws": "AWS/AwsRoot",
    "azure": "Azure/AzureRoot",
    "gcp": "GCP/GcpRoot",
}

TEST_RESULT_FIELDS = ["awsTestResult", "azureTestResult", "gcpTestResult"]

READ_ONLY_FIELDS = ["subGroups"]

MASKED_VALUE_PATTERN = "****"


def list_cloud_root_groups(
    client: LogicMonitorClient,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """List cloud root groups from LogicMonitor.

    Args:
        client: LogicMonitor API client.
        provider: Provider name (aws, azure, gcp) to filter by, or None for all.

    Returns:
        List of raw group dicts from the LM API.

    Raises:
        ValueError: If provider name is not recognized.
    """
    if provider is not None:
        provider = provider.lower()
        if provider not in CLOUD_GROUP_TYPES:
            raise ValueError(f"Unknown provider: {provider}. Must be one of: {list(CLOUD_GROUP_TYPES)}")
        group_types = [CLOUD_GROUP_TYPES[provider]]
    else:
        group_types = list(CLOUD_GROUP_TYPES.values())

    groups: list[dict[str, Any]] = []
    for group_type in group_types:
        response = client.get(
            "/device/groups",
            params={
                "filter": f'groupType:"{group_type}"',
                "fields": "id,name,description,parentId,groupType,customProperties,extra",
            },
        )
        data_wrapper = response.get("data", response)
        if not isinstance(data_wrapper, dict):
            logger.warning(
                "Unexpected response shape listing cloud root groups for %s: %s",
                group_type,
                type(data_wrapper).__name__,
            )
            continue
        items = data_wrapper.get("items", [])
        groups.extend(items)

    return groups


def prepare_resync_payload(
    group_data: dict[str, Any],
    extra_modifications: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare a group payload for the resync PUT request.

    Deep-copies the group data, strips read-only fields, and optionally
    merges modifications into the extra field.

    Args:
        group_data: Raw group dict from GET response.
        extra_modifications: Dict to deep-merge into the extra field.

    Returns:
        Sanitized payload ready for PUT.
    """
    payload = copy.deepcopy(group_data)

    for field in READ_ONLY_FIELDS:
        payload.pop(field, None)

    if extra_modifications and "extra" in payload:
        _deep_merge(payload["extra"], extra_modifications)
    elif extra_modifications:
        payload["extra"] = copy.deepcopy(extra_modifications)

    return payload


def check_masked_credentials(payload: dict[str, Any]) -> list[str]:
    """Check for masked credential values in a group payload.

    Azure GET responses mask secretKey as '****'. Sending this back
    in a PUT will fail credential validation.

    Args:
        payload: Group payload dict (before or after preparation).

    Returns:
        List of field names that contain masked values.
    """
    extra = payload.get("extra", {})
    account = extra.get("account", {})

    masked_fields: list[str] = []
    for key, value in account.items():
        if isinstance(value, str) and value == MASKED_VALUE_PATTERN:
            masked_fields.append(key)

    return masked_fields


def resync_group(
    client: LogicMonitorClient,
    group_id: int,
    extra_modifications: dict[str, Any] | None = None,
    credential_overrides: dict[str, str] | None = None,
    dry_run: bool = False,
) -> ResyncResult:
    """Resync a cloud root group by performing a full GET then PUT.

    The PUT triggers LM's cloud sync engine: credential validation,
    region re-evaluation, and service re-discovery.

    Args:
        client: LogicMonitor API client.
        group_id: LM device group ID.
        extra_modifications: Optional modifications to merge into extra field.
        credential_overrides: Key-value pairs to override in extra.account
            (e.g., {"secretKey": "real-value"} for masked Azure credentials).
        dry_run: If True, perform GET but skip PUT.

    Returns:
        ResyncResult with status, test results, and any warnings.
    """
    try:
        group_data = client.get(f"/device/groups/{group_id}")
    except LMAPIError as e:
        return ResyncResult(
            group_id=group_id,
            group_name="",
            group_type="",
            status="failed",
            error=str(e),
        )

    group_name = group_data.get("name", "")
    group_type = group_data.get("groupType", "")

    if "extra" not in group_data or "account" not in group_data.get("extra", {}):
        return ResyncResult(
            group_id=group_id,
            group_name=group_name,
            group_type=group_type,
            status="failed",
            error="GET response missing extra.account -- aborting to prevent data loss",
        )

    payload = prepare_resync_payload(group_data, extra_modifications)
    masked = check_masked_credentials(payload)

    if credential_overrides and "extra" in payload and "account" in payload["extra"]:
        for key, value in credential_overrides.items():
            payload["extra"]["account"][key] = value
        masked = [f for f in masked if f not in credential_overrides]

    if dry_run:
        return ResyncResult(
            group_id=group_id,
            group_name=group_name,
            group_type=group_type,
            status="dry_run",
            masked_fields=masked,
        )

    try:
        response = client.put(f"/device/groups/{group_id}", json=payload)
    except LMAPIError as e:
        return ResyncResult(
            group_id=group_id,
            group_name=group_name,
            group_type=group_type,
            status="failed",
            masked_fields=masked,
            error=str(e),
        )

    test_results: dict[str, Any] = {}
    for field in TEST_RESULT_FIELDS:
        if field in response:
            test_results[field] = response[field]

    return ResyncResult(
        group_id=group_id,
        group_name=group_name,
        group_type=group_type,
        status="success",
        test_results=test_results,
        masked_fields=masked,
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Deep-merge override dict into base dict (in-place).

    For nested dicts, recursively merges. For all other types,
    the override value replaces the base value.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
