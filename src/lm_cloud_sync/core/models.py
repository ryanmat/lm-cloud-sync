# Description: Data models for cloud resources and LogicMonitor groups.
# Description: Defines shared data structures for AWS, Azure, and GCP resources.

"""Data models for cloud resources and LogicMonitor groups."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class SyncAction(str, Enum):
    """Actions that can be taken during sync."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SKIP = "skip"


@dataclass(kw_only=True)
class CloudResource:
    """Base class for cloud resources (accounts, subscriptions, projects)."""

    provider: CloudProvider
    resource_id: str
    display_name: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class AWSAccount(CloudResource):
    """AWS account discovered from Organizations API."""

    provider: CloudProvider = CloudProvider.AWS
    email: str | None = None
    arn: str | None = None


@dataclass(kw_only=True)
class AzureSubscription(CloudResource):
    """Azure subscription discovered from Management API."""

    provider: CloudProvider = CloudProvider.AZURE
    tenant_id: str | None = None


@dataclass(kw_only=True)
class GCPProject(CloudResource):
    """GCP project discovered from Resource Manager API."""

    provider: CloudProvider = CloudProvider.GCP
    project_number: str | None = None
    parent: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    create_time: datetime | None = None


class ProjectState(str, Enum):
    """GCP Project lifecycle state."""

    ACTIVE = "ACTIVE"
    DELETE_REQUESTED = "DELETE_REQUESTED"
    DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"


class TagOperation(str, Enum):
    """Tag filter operation type."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


class TagFilter(BaseModel):
    """Tag filter for cloud resource discovery in LM."""

    name: str = Field(..., description="Tag name")
    operation: TagOperation = Field(default=TagOperation.INCLUDE)
    value: str


class ServiceConfig(BaseModel):
    """Configuration for a specific cloud service in LM."""

    use_default: bool = Field(default=True)
    select_all: bool = Field(default=False)
    monitoring_regions: list[str] = Field(default_factory=list)
    tags: list[TagFilter] = Field(default_factory=list)
    name_filter: list[str] = Field(default_factory=list)
    dead_operation: str = Field(default="KEEP_7_DAYS")
    disable_terminated_host_alerting: bool = Field(default=True)
    device_display_name_template: str = Field(default="")

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to LogicMonitor API format."""
        return {
            "useDefault": self.use_default,
            "selectAll": self.select_all,
            "monitoringRegions": self.monitoring_regions,
            "tags": [
                {
                    "name": t.name,
                    "operation": t.operation.value,
                    "value": t.value,
                }
                for t in self.tags
            ],
            "nameFilter": self.name_filter,
            "deadOperation": self.dead_operation,
            "disableTerminatedHostAlerting": self.disable_terminated_host_alerting,
        }


class LMCloudGroup(BaseModel):
    """LogicMonitor cloud integration group (AWS, Azure, or GCP)."""

    model_config = ConfigDict(frozen=False)

    id: int | None = Field(default=None, description="LM group ID")
    name: str
    provider: CloudProvider
    resource_id: str  # AWS Account ID, Azure Subscription ID, or GCP Project ID
    description: str = Field(default="")
    parent_id: int = Field(default=1)
    custom_properties: dict[str, str] = Field(default_factory=dict)
    netscan_frequency: str = Field(default="0 * * * *")
    default_config: ServiceConfig = Field(default_factory=ServiceConfig)
    services: dict[str, ServiceConfig] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Result of a sync operation."""

    provider: CloudProvider | None = None
    created: list[str] = Field(default_factory=list, description="Resource IDs created")
    updated: list[str] = Field(default_factory=list, description="Resource IDs updated")
    deleted: list[str] = Field(default_factory=list, description="Resource IDs deleted")
    skipped: list[str] = Field(
        default_factory=list, description="Resource IDs skipped (already exist)"
    )
    failed: dict[str, str] = Field(default_factory=dict, description="Resource ID -> error message")
    dry_run: bool = Field(default=False, description="Whether this was a dry run")

    @property
    def total_processed(self) -> int:
        """Total number of resources processed."""
        return (
            len(self.created)
            + len(self.updated)
            + len(self.deleted)
            + len(self.skipped)
            + len(self.failed)
        )

    @property
    def success_count(self) -> int:
        """Number of successfully processed resources."""
        return len(self.created) + len(self.updated) + len(self.deleted) + len(self.skipped)

    @property
    def has_failures(self) -> bool:
        """Check if any failures occurred."""
        return len(self.failed) > 0

    def merge(self, other: "SyncResult") -> "SyncResult":
        """Merge another SyncResult into this one."""
        return SyncResult(
            provider=self.provider,
            created=self.created + other.created,
            updated=self.updated + other.updated,
            deleted=self.deleted + other.deleted,
            skipped=self.skipped + other.skipped,
            failed={**self.failed, **other.failed},
            dry_run=self.dry_run or other.dry_run,
        )


@dataclass(kw_only=True)
class ResyncResult:
    """Result of a resync operation on a single cloud root group."""

    group_id: int
    group_name: str
    group_type: str
    status: str  # "success", "dry_run", "failed", "warning"
    test_results: dict[str, Any] = field(default_factory=dict)
    masked_fields: list[str] = field(default_factory=list)
    error: str | None = None
