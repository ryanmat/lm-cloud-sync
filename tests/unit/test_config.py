# Description: Unit tests for configuration management.
# Description: Tests auth auto-detection, env overrides, and YAML loading.

"""Unit tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest

from lm_cloud_sync.core.config import Settings
from lm_cloud_sync.core.exceptions import ConfigurationError


class TestAuthAutoDetectBearer:
    """Tests for bearer token auto-detection."""

    def test_bearer_token_only_infers_bearer(self) -> None:
        """Setting only LM_BEARER_TOKEN should auto-detect bearer auth."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_BEARER_TOKEN": "lmb_test123",
        }
        settings = Settings.from_env(env=env)
        assert settings.logicmonitor.auth_method == "bearer"
        assert settings.logicmonitor.bearer_token is not None

    def test_bearer_with_explicit_auth_method(self) -> None:
        """Explicit auth_method=bearer with bearer token should work."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_BEARER_TOKEN": "lmb_test123",
            "LM_AUTH_METHOD": "bearer",
        }
        settings = Settings.from_env(env=env)
        assert settings.logicmonitor.auth_method == "bearer"


class TestAuthAutoDetectLMv1:
    """Tests for LMv1 auth auto-detection."""

    def test_access_keys_only_infers_lmv1(self) -> None:
        """Setting only LM_ACCESS_ID + LM_ACCESS_KEY should auto-detect lmv1."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_ACCESS_ID": "test-id",
            "LM_ACCESS_KEY": "test-key",
        }
        settings = Settings.from_env(env=env)
        assert settings.logicmonitor.auth_method == "lmv1"
        assert settings.logicmonitor.access_id == "test-id"

    def test_access_keys_with_explicit_lmv1(self) -> None:
        """Explicit auth_method=lmv1 with access keys should work."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_ACCESS_ID": "test-id",
            "LM_ACCESS_KEY": "test-key",
            "LM_AUTH_METHOD": "lmv1",
        }
        settings = Settings.from_env(env=env)
        assert settings.logicmonitor.auth_method == "lmv1"

    def test_partial_lmv1_creds_raises(self) -> None:
        """LM_ACCESS_ID without LM_ACCESS_KEY should raise."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_ACCESS_ID": "test-id",
            "LM_AUTH_METHOD": "lmv1",
        }
        with pytest.raises(ConfigurationError):
            Settings.from_env(env=env)


class TestAuthAutoDetectEdgeCases:
    """Tests for auth auto-detection edge cases."""

    def test_no_credentials_raises(self) -> None:
        """No credentials at all should raise ConfigurationError."""
        env = {"LM_COMPANY": "test-co"}
        with pytest.raises(ConfigurationError):
            Settings.from_env(env=env)

    def test_missing_company_raises(self) -> None:
        """Missing LM_COMPANY should raise ConfigurationError."""
        env = {"LM_BEARER_TOKEN": "lmb_test123"}
        with pytest.raises(ConfigurationError):
            Settings.from_env(env=env)

    def test_explicit_auth_method_honored_over_auto_detect(self) -> None:
        """Explicit auth_method should override auto-detection."""
        env = {
            "LM_COMPANY": "test-co",
            "LM_BEARER_TOKEN": "lmb_test123",
            "LM_ACCESS_ID": "test-id",
            "LM_ACCESS_KEY": "test-key",
            "LM_AUTH_METHOD": "lmv1",
        }
        settings = Settings.from_env(env=env)
        assert settings.logicmonitor.auth_method == "lmv1"


class TestEnvOverrideAuthMethod:
    """Tests for LM_AUTH_METHOD in _apply_env_overrides (YAML path)."""

    def test_auth_method_applied_from_env(self) -> None:
        """LM_AUTH_METHOD should be applied in the YAML+env path."""
        config_data: dict = {}
        env = {
            "LM_COMPANY": "test-co",
            "LM_ACCESS_ID": "test-id",
            "LM_ACCESS_KEY": "test-key",
            "LM_AUTH_METHOD": "lmv1",
        }
        result = Settings._apply_env_overrides(config_data, env)
        assert result["logicmonitor"]["auth_method"] == "lmv1"
