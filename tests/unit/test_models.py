"""Tests for data models."""


from lm_cloud_sync.core.models import (
    CloudProvider,
    GCPProject,
    LMCloudGroup,
    ServiceConfig,
    SyncResult,
)


class TestCloudProvider:
    """Tests for CloudProvider enum."""

    def test_provider_values(self) -> None:
        """Test provider enum values."""
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.GCP.value == "gcp"


class TestGCPProject:
    """Tests for GCPProject model."""

    def test_create_project(self) -> None:
        """Test creating a GCP project."""
        project = GCPProject(
            resource_id="my-project",
            display_name="My Project",
            status="ACTIVE",
            project_number="123456789",
        )

        assert project.provider == CloudProvider.GCP
        assert project.resource_id == "my-project"
        assert project.display_name == "My Project"
        assert project.status == "ACTIVE"

    def test_project_with_labels(self) -> None:
        """Test project with labels."""
        project = GCPProject(
            resource_id="my-project",
            display_name="My Project",
            status="ACTIVE",
            labels={"env": "prod", "team": "platform"},
        )

        assert project.labels["env"] == "prod"
        assert project.labels["team"] == "platform"


class TestLMCloudGroup:
    """Tests for LMCloudGroup model."""

    def test_create_group(self) -> None:
        """Test creating an LM cloud group."""
        group = LMCloudGroup(
            id=123,
            name="GCP - my-project",
            provider=CloudProvider.GCP,
            resource_id="my-project",
            parent_id=1,
        )

        assert group.id == 123
        assert group.name == "GCP - my-project"
        assert group.provider == CloudProvider.GCP
        assert group.resource_id == "my-project"

    def test_group_with_custom_properties(self) -> None:
        """Test group with custom properties."""
        group = LMCloudGroup(
            id=123,
            name="GCP - my-project",
            provider=CloudProvider.GCP,
            resource_id="my-project",
            custom_properties={"lm.cloud.managed_by": "lm-cloud-sync"},
        )

        assert group.custom_properties["lm.cloud.managed_by"] == "lm-cloud-sync"


class TestSyncResult:
    """Tests for SyncResult model."""

    def test_empty_result(self) -> None:
        """Test empty sync result."""
        result = SyncResult()

        assert result.total_processed == 0
        assert result.success_count == 0
        assert not result.has_failures

    def test_result_with_operations(self) -> None:
        """Test sync result with operations."""
        result = SyncResult(
            provider=CloudProvider.GCP,
            created=["project-1", "project-2"],
            skipped=["project-3"],
            deleted=["project-4"],
            failed={"project-5": "Error message"},
        )

        assert result.total_processed == 5
        assert result.success_count == 4
        assert result.has_failures
        assert len(result.created) == 2
        assert len(result.failed) == 1

    def test_merge_results(self) -> None:
        """Test merging two sync results."""
        result1 = SyncResult(
            provider=CloudProvider.GCP,
            created=["project-1"],
            skipped=["project-2"],
        )
        result2 = SyncResult(
            provider=CloudProvider.GCP,
            created=["project-3"],
            failed={"project-4": "Error"},
        )

        merged = result1.merge(result2)

        assert len(merged.created) == 2
        assert len(merged.skipped) == 1
        assert len(merged.failed) == 1


class TestServiceConfig:
    """Tests for ServiceConfig model."""

    def test_default_config(self) -> None:
        """Test default service config."""
        config = ServiceConfig()

        assert config.use_default is True
        assert config.select_all is False
        assert config.dead_operation == "KEEP_7_DAYS"

    def test_to_api_dict(self) -> None:
        """Test conversion to API format."""
        config = ServiceConfig(
            use_default=True,
            monitoring_regions=["us-central1"],
            dead_operation="KEEP_7_DAYS",
        )

        api_dict = config.to_api_dict()

        assert api_dict["useDefault"] is True
        assert api_dict["monitoringRegions"] == ["us-central1"]
        assert api_dict["deadOperation"] == "KEEP_7_DAYS"
