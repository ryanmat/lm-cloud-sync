# Description: GCP project discovery module.
# Description: Discovers GCP projects using Resource Manager API for LM integration.

"""GCP project discovery module."""

from __future__ import annotations

import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from google.api_core import exceptions as gcp_exceptions
from google.cloud import resourcemanager_v3
from google.oauth2 import service_account

from lm_cloud_sync.core.exceptions import CloudAPIError
from lm_cloud_sync.core.models import CloudProvider, GCPProject, ProjectState

if TYPE_CHECKING:
    from google.auth.credentials import Credentials

logger = logging.getLogger(__name__)


class GCPProjectDiscovery:
    """Discovers GCP projects accessible to the authenticated identity."""

    def __init__(self, credentials: Credentials | None = None) -> None:
        """Initialize discovery with optional credentials.

        Args:
            credentials: GCP credentials. If None, uses application default credentials.
        """
        self._credentials = credentials
        self._client = resourcemanager_v3.ProjectsClient(credentials=credentials)

    @classmethod
    def from_service_account_file(cls, path: str | Path) -> GCPProjectDiscovery:
        """Create discovery instance from service account JSON file.

        Args:
            path: Path to service account JSON key file.

        Returns:
            Configured GCPProjectDiscovery instance.
        """
        credentials = service_account.Credentials.from_service_account_file(str(path))
        return cls(credentials=credentials)

    def discover_projects(
        self,
        *,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        exclude_projects: list[str] | None = None,
        required_labels: dict[str, str] | None = None,
        excluded_labels: dict[str, str] | None = None,
    ) -> list[GCPProject]:
        """Discover GCP projects with optional filtering.

        Args:
            include_patterns: Glob patterns for project IDs to include.
            exclude_patterns: Glob patterns for project IDs to exclude.
            exclude_projects: Specific project IDs to exclude.
            required_labels: Labels that must be present with matching values.
            excluded_labels: Labels that exclude a project if present.

        Returns:
            List of discovered GCPProject objects.

        Raises:
            CloudAPIError: If the GCP API call fails.
        """
        try:
            raw_projects = list(self._client.search_projects())
        except gcp_exceptions.GoogleAPICallError as e:
            raise CloudAPIError(str(e), provider="gcp") from e

        projects = []
        for raw_project in raw_projects:
            if not self._should_include(
                raw_project,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                exclude_projects=exclude_projects,
                required_labels=required_labels,
                excluded_labels=excluded_labels,
            ):
                continue

            project = self._convert_project(raw_project)
            projects.append(project)

        return projects

    def _should_include(
        self,
        project: resourcemanager_v3.Project,
        *,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        exclude_projects: list[str] | None,
        required_labels: dict[str, str] | None,
        excluded_labels: dict[str, str] | None,
    ) -> bool:
        """Determine if a project should be included based on filters."""
        project_id = project.project_id
        labels = dict(project.labels) if project.labels else {}

        # Only include ACTIVE projects
        if project.state.name != "ACTIVE":
            return False

        # Check include patterns
        if include_patterns:
            if not any(fnmatch.fnmatch(project_id, p) for p in include_patterns):
                return False

        # Check exclude patterns
        if exclude_patterns:
            if any(fnmatch.fnmatch(project_id, p) for p in exclude_patterns):
                return False

        # Check explicit project exclusions
        if exclude_projects and project_id in exclude_projects:
            return False

        # Check required labels
        if required_labels:
            for key, value in required_labels.items():
                if labels.get(key) != value:
                    return False

        # Check excluded labels
        if excluded_labels:
            for key, value in excluded_labels.items():
                if labels.get(key) == value:
                    return False

        return True

    def _convert_project(self, raw_project: resourcemanager_v3.Project) -> GCPProject:
        """Convert GCP API project to our model."""
        project_number = raw_project.name.split("/")[-1] if raw_project.name else ""

        state_name = raw_project.state.name
        if state_name not in ProjectState.__members__:
            logger.warning(
                "Unknown project state '%s' for project '%s', treating as ACTIVE",
                state_name,
                raw_project.project_id,
            )
            state = ProjectState.ACTIVE
        else:
            state = ProjectState(state_name)

        create_time: datetime | None = None
        if raw_project.create_time:
            create_time = raw_project.create_time

        return GCPProject(
            provider=CloudProvider.GCP,
            resource_id=raw_project.project_id,
            display_name=raw_project.display_name or raw_project.project_id,
            status=state.value,
            project_number=project_number,
            parent=raw_project.parent or None,
            labels=dict(raw_project.labels) if raw_project.labels else {},
            create_time=create_time,
        )
