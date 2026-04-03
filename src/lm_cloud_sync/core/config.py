# Description: Configuration management for lm-cloud-sync.
# Description: Handles YAML config loading and environment variable overrides.

"""Configuration management for lm-cloud-sync."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from lm_cloud_sync import __version__
from lm_cloud_sync.core.exceptions import ConfigurationError


class LogicMonitorConfig(BaseModel):
    """LogicMonitor API configuration."""

    company: str = Field(..., description="LM portal company name")
    auth_method: str = Field(default="bearer", description="Authentication method: bearer or lmv1")
    parent_group_id: int = Field(default=1, description="Parent group ID for cloud integrations")

    bearer_token: SecretStr | None = Field(default=None, description="Bearer token for auth")
    access_id: str | None = Field(default=None, description="LMv1 access ID")
    access_key: SecretStr | None = Field(default=None, description="LMv1 access key")

    @field_validator("auth_method")
    @classmethod
    def validate_auth_method(cls, v: str) -> str:
        """Validate auth_method is either bearer or lmv1."""
        if v not in ("bearer", "lmv1"):
            raise ValueError("auth_method must be 'bearer' or 'lmv1'")
        return v


class ProviderFilters(BaseModel):
    """Base filters for cloud resource discovery."""

    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    exclude_resources: list[str] = Field(default_factory=list)
    required_tags: dict[str, str] = Field(default_factory=dict)
    excluded_tags: dict[str, str] = Field(default_factory=dict)


class GCPConfig(BaseModel):
    """GCP-specific configuration."""

    enabled: bool = Field(default=True)
    parent_group_id: int | None = Field(default=None, description="Override parent group for GCP")
    organization_id: str | None = Field(default=None, description="GCP organization ID")
    service_account_key_path: Path | None = Field(
        default=None, description="Path to service account JSON key"
    )
    filters: ProviderFilters = Field(default_factory=ProviderFilters)
    regions: list[str] = Field(
        default_factory=lambda: ["us-central1", "us-east1"], description="GCP regions to monitor"
    )
    services: list[str] = Field(
        default_factory=lambda: ["COMPUTEENGINE", "CLOUDSQL"], description="GCP services to monitor"
    )


class AWSConfig(BaseModel):
    """AWS-specific configuration."""

    enabled: bool = Field(default=False)
    parent_group_id: int | None = Field(default=None, description="Override parent group for AWS")
    role_name: str = Field(default="LogicMonitorRole", description="IAM role name to assume")
    filters: ProviderFilters = Field(default_factory=ProviderFilters)
    regions: list[str] = Field(
        default_factory=lambda: ["us-east-1", "us-west-2"], description="AWS regions to monitor"
    )
    services: list[str] = Field(
        default_factory=lambda: ["EC2", "RDS", "S3"], description="AWS services to monitor"
    )


class AzureConfig(BaseModel):
    """Azure-specific configuration."""

    enabled: bool = Field(default=False)
    parent_group_id: int | None = Field(default=None, description="Override parent group for Azure")
    tenant_id: str | None = Field(default=None, description="Azure AD tenant ID")
    client_id: str | None = Field(default=None, description="Service principal client ID")
    client_secret: SecretStr | None = Field(default=None, description="Service principal secret")
    filters: ProviderFilters = Field(default_factory=ProviderFilters)
    regions: list[str] = Field(
        default_factory=lambda: ["eastus", "westus2"], description="Azure regions to monitor"
    )
    services: list[str] = Field(
        default_factory=lambda: ["VIRTUALMACHINE", "SQLDATABASE"],
        description="Azure services to monitor",
    )


class MonitoringConfig(BaseModel):
    """Default monitoring settings for new cloud integrations."""

    netscan_frequency: str = Field(default="0 * * * *", description="Cron schedule for netscans")
    dead_operation: str = Field(
        default="KEEP_7_DAYS", description="Action for terminated instances"
    )
    disable_terminated_alerting: bool = Field(
        default=True, description="Disable alerting on terminated hosts"
    )

    @field_validator("dead_operation")
    @classmethod
    def validate_dead_operation(cls, v: str) -> str:
        """Validate dead_operation is a valid value."""
        valid_values = ("MANUALLY", "KEEP_7_DAYS", "KEEP_14_DAYS", "KEEP_30_DAYS", "IMMEDIATELY")
        if v not in valid_values:
            raise ValueError(f"dead_operation must be one of {valid_values}")
        return v


class SyncConfig(BaseModel):
    """Sync behavior configuration."""

    dry_run: bool = Field(default=False, description="Preview changes without applying")
    auto_discover: bool = Field(default=False, description="Use org-level discovery APIs")
    create_missing: bool = Field(default=True, description="Create integrations for new resources")
    update_existing: bool = Field(
        default=False, description="Update config on existing integrations"
    )
    delete_orphans: bool = Field(
        default=False, description="Delete LM groups for removed cloud resources"
    )
    group_name_template: str = Field(
        default="{provider} - {resource_id}", description="Template for LM group names"
    )
    custom_properties: dict[str, str] = Field(
        default_factory=lambda: {
            "lm.cloud.managed_by": "lm-cloud-sync",
            "lm.cloud.version": __version__,
        },
        description="Custom properties for all groups",
    )


class EnvSettings(BaseSettings):
    """Settings class for reading from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_prefix="LM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LogicMonitor settings (LM_ prefix applied automatically)
    company: str | None = Field(default=None, description="LM portal company name")
    bearer_token: SecretStr | None = Field(default=None, description="Bearer token for auth")
    access_id: str | None = Field(default=None, description="LMv1 access ID")
    access_key: SecretStr | None = Field(default=None, description="LMv1 access key")
    auth_method: str = Field(default="bearer", description="Authentication method")
    parent_group_id: int = Field(default=1, description="Parent group ID")


class GCPEnvSettings(BaseSettings):
    """GCP-specific environment settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_application_credentials: Path | None = Field(
        default=None, description="Path to GCP service account key"
    )
    gcp_sa_key_path: Path | None = Field(
        default=None, description="Alternate path to GCP service account key"
    )


class AWSEnvSettings(BaseSettings):
    """AWS-specific environment settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_role_name: str = Field(
        default="LogicMonitorRole", description="IAM role name to assume"
    )
    aws_regions: str | None = Field(
        default=None, description="Comma-separated list of AWS regions"
    )


class AzureEnvSettings(BaseSettings):
    """Azure-specific environment settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_tenant_id: str | None = Field(
        default=None, description="Azure AD tenant ID"
    )
    azure_client_id: str | None = Field(
        default=None, description="Service Principal client/application ID"
    )
    azure_client_secret: str | None = Field(
        default=None, description="Service Principal secret"
    )
    azure_regions: str | None = Field(
        default=None, description="Comma-separated list of Azure regions"
    )


class Settings(BaseModel):
    """Main settings class combining all configuration sections."""

    logicmonitor: LogicMonitorConfig
    gcp: GCPConfig = Field(default_factory=GCPConfig)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    azure: AzureConfig = Field(default_factory=AzureConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "Settings":
        """Validate that appropriate auth credentials are provided."""
        lm = self.logicmonitor

        if lm.auth_method == "bearer":
            if not lm.bearer_token:
                raise ValueError(
                    "bearer_token is required when auth_method is 'bearer'. "
                    "Set LM_BEARER_TOKEN environment variable."
                )
        elif lm.auth_method == "lmv1" and (not lm.access_id or not lm.access_key):
            raise ValueError(
                "Both access_id and access_key are required when auth_method is 'lmv1'. "
                "Set LM_ACCESS_ID and LM_ACCESS_KEY environment variables."
            )

        return self

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        """Create settings from environment variables and .env file."""
        if env is not None:
            config_data = cls._apply_env_overrides({}, env)
        else:
            lm_env = EnvSettings()
            gcp_env = GCPEnvSettings()
            aws_env = AWSEnvSettings()
            azure_env = AzureEnvSettings()

            config_data: dict[str, Any] = {
                "logicmonitor": {
                    "company": lm_env.company,
                    "bearer_token": lm_env.bearer_token,
                    "access_id": lm_env.access_id,
                    "access_key": lm_env.access_key,
                    "auth_method": lm_env.auth_method,
                    "parent_group_id": lm_env.parent_group_id,
                },
                "gcp": {},
                "aws": {"enabled": False},
                "azure": {"enabled": False},
            }

            # Check for GCP service account key
            sa_key_path = gcp_env.gcp_sa_key_path or gcp_env.google_application_credentials
            if sa_key_path:
                config_data["gcp"]["service_account_key_path"] = sa_key_path

            # AWS settings
            if aws_env.aws_role_name:
                config_data["aws"]["role_name"] = aws_env.aws_role_name
            if aws_env.aws_regions:
                config_data["aws"]["regions"] = [
                    r.strip() for r in aws_env.aws_regions.split(",")
                ]

            # Azure settings
            if azure_env.azure_tenant_id:
                config_data["azure"]["tenant_id"] = azure_env.azure_tenant_id
            if azure_env.azure_client_id:
                config_data["azure"]["client_id"] = azure_env.azure_client_id
            if azure_env.azure_client_secret:
                config_data["azure"]["client_secret"] = azure_env.azure_client_secret
            if azure_env.azure_regions:
                config_data["azure"]["regions"] = [
                    r.strip() for r in azure_env.azure_regions.split(",")
                ]

        try:
            return cls.model_validate(config_data)
        except Exception as e:
            error_msg = str(e)
            if "Field required" in error_msg and "company" in error_msg:
                raise ConfigurationError("Missing LM_COMPANY environment variable") from e
            raise ConfigurationError(f"Configuration validation failed: {error_msg}") from e

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        env_overrides: dict[str, str] | None = None,
    ) -> "Settings":
        """Load settings from a YAML file with environment variable overrides."""
        import os

        if env_overrides is None:
            env_overrides = dict(os.environ)

        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path) as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}") from e

        config_data = cls._apply_env_overrides(config_data, env_overrides)

        try:
            return cls.model_validate(config_data)
        except Exception as e:
            error_msg = str(e)
            if "Field required" in error_msg and "company" in error_msg:
                raise ConfigurationError("Missing required field: company") from e
            raise ConfigurationError(f"Configuration validation failed: {error_msg}") from e

    @classmethod
    def _apply_env_overrides(
        cls, config_data: dict[str, Any], env: dict[str, str]
    ) -> dict[str, Any]:
        """Apply environment variable overrides to config data."""
        if "logicmonitor" not in config_data:
            config_data["logicmonitor"] = {}

        lm = config_data["logicmonitor"]

        # LM credentials
        if "LM_BEARER_TOKEN" in env:
            lm["bearer_token"] = env["LM_BEARER_TOKEN"]
        if "LM_ACCESS_ID" in env:
            lm["access_id"] = env["LM_ACCESS_ID"]
        if "LM_ACCESS_KEY" in env:
            lm["access_key"] = env["LM_ACCESS_KEY"]
        if "LM_COMPANY" in env:
            lm["company"] = env["LM_COMPANY"]

        # GCP
        if "gcp" not in config_data:
            config_data["gcp"] = {}
        gcp = config_data["gcp"]
        if "GOOGLE_APPLICATION_CREDENTIALS" in env:
            gcp["service_account_key_path"] = env["GOOGLE_APPLICATION_CREDENTIALS"]
        if "GCP_SA_KEY_PATH" in env:
            gcp["service_account_key_path"] = env["GCP_SA_KEY_PATH"]

        # AWS
        if "aws" not in config_data:
            config_data["aws"] = {"enabled": False}
        aws = config_data["aws"]
        if "AWS_ROLE_NAME" in env:
            aws["role_name"] = env["AWS_ROLE_NAME"]
        if "AWS_REGIONS" in env:
            aws["regions"] = [r.strip() for r in env["AWS_REGIONS"].split(",")]

        # Azure
        if "azure" not in config_data:
            config_data["azure"] = {"enabled": False}
        azure = config_data["azure"]
        if "AZURE_TENANT_ID" in env:
            azure["tenant_id"] = env["AZURE_TENANT_ID"]
        if "AZURE_CLIENT_ID" in env:
            azure["client_id"] = env["AZURE_CLIENT_ID"]
        if "AZURE_CLIENT_SECRET" in env:
            azure["client_secret"] = env["AZURE_CLIENT_SECRET"]
        if "AZURE_REGIONS" in env:
            azure["regions"] = [r.strip() for r in env["AZURE_REGIONS"].split(",")]

        return config_data
