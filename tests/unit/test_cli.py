"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner

from lm_cloud_sync import __version__
from lm_cloud_sync.cli.main import main


class TestMainCLI:
    """Tests for main CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_version(self, runner: CliRunner) -> None:
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "LM Cloud Sync" in result.output
        assert "gcp" in result.output

    def test_gcp_help(self, runner: CliRunner) -> None:
        """Test gcp --help."""
        result = runner.invoke(main, ["gcp", "--help"])
        assert result.exit_code == 0
        assert "discover" in result.output
        assert "sync" in result.output
        assert "status" in result.output


class TestConfigCLI:
    """Tests for config CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_config_init(self, runner: CliRunner) -> None:
        """Test config init command."""
        from pathlib import Path

        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "init", "-o", "test-config.yaml"])
            assert result.exit_code == 0
            assert "Created configuration file" in result.output

            # Verify file was created
            assert Path("test-config.yaml").exists()

    def test_config_init_file_exists(self, runner: CliRunner) -> None:
        """Test config init when file already exists."""
        from pathlib import Path

        with runner.isolated_filesystem():
            # Create the file first
            Path("config.yaml").write_text("existing content")

            result = runner.invoke(main, ["config", "init"])
            assert result.exit_code == 1
            assert "already exists" in result.output
