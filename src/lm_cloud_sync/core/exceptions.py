# Description: Custom exception hierarchy for lm-cloud-sync.
# Description: Defines error types for authentication, configuration, and API failures.

"""Custom exception hierarchy for lm-cloud-sync."""

from typing import Any


class LMCloudSyncError(Exception):
    """Base exception for all lm-cloud-sync errors."""

    pass


class ConfigurationError(LMCloudSyncError):
    """Configuration is invalid or missing."""

    pass


class AuthenticationError(LMCloudSyncError):
    """Authentication failed."""

    pass


class LMAPIError(LMCloudSyncError):
    """LogicMonitor API returned an error."""

    def __init__(self, message: str, status_code: int, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class RateLimitError(LMAPIError):
    """Rate limit exceeded."""

    pass


class CloudAPIError(LMCloudSyncError):
    """Cloud provider API returned an error."""

    def __init__(self, message: str, provider: str):
        super().__init__(message)
        self.provider = provider


class ResourceNotFoundError(LMCloudSyncError):
    """Cloud resource not found."""

    def __init__(self, message: str, provider: str, resource_id: str):
        super().__init__(message)
        self.provider = provider
        self.resource_id = resource_id


class GroupExistsError(LMCloudSyncError):
    """LM group already exists for this cloud resource."""

    pass


class DiscoveryError(LMCloudSyncError):
    """Error during cloud resource discovery."""

    pass
