# Description: Shared CLI helper functions for lm-cloud-sync.
# Description: Provides common settings loading and LM client creation used across all CLI modules.

"""Shared CLI helper functions."""

from __future__ import annotations

from pathlib import Path

from lm_cloud_sync.core.config import Settings
from lm_cloud_sync.core.exceptions import ConfigurationError
from lm_cloud_sync.core.lm_client import LogicMonitorClient


def get_settings(config_path: str | None = None) -> Settings:
    """Load settings from config file or environment."""
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise ConfigurationError(f"Config file not found: {config_path}")
        return Settings.from_yaml(path)
    return Settings.from_env()


def get_lm_client(settings: Settings) -> LogicMonitorClient:
    """Create LogicMonitor client from settings."""
    lm = settings.logicmonitor
    if lm.bearer_token:
        return LogicMonitorClient(company=lm.company, bearer_token=lm.bearer_token)
    elif lm.access_id and lm.access_key:
        return LogicMonitorClient(
            company=lm.company, access_id=lm.access_id, access_key=lm.access_key
        )
    else:
        raise ConfigurationError("No valid LM credentials configured")
