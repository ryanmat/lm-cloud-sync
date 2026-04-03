# Description: Main CLI entry point for lm-cloud-sync.
# Description: Handles command routing and configuration for multi-cloud operations.

"""Main CLI entry point for lm-cloud-sync."""

import click
from rich.console import Console

from lm_cloud_sync import __version__
from lm_cloud_sync.cli.aws import aws
from lm_cloud_sync.cli.azure import azure
from lm_cloud_sync.cli.gcp import gcp

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="lm-cloud-sync")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """LM Cloud Sync - Multi-cloud automation for LogicMonitor integrations.

    Sync cloud resources (AWS accounts, Azure subscriptions, GCP projects)
    to LogicMonitor as device groups.

    \b
    Examples:
        lm-cloud-sync gcp discover
        lm-cloud-sync gcp sync --dry-run
        lm-cloud-sync gcp sync --yes
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# Register provider commands
main.add_command(gcp)
main.add_command(aws)
main.add_command(azure)


@main.group()
@click.pass_context
def all(ctx: click.Context) -> None:
    """Multi-cloud operations (coming soon).

    Sync all cloud providers at once.
    """
    console.print("[yellow]Multi-cloud sync coming in Phase 4[/yellow]")


@main.group()
def config() -> None:
    """Configuration management."""
    pass


@config.command("init")
@click.option("--output", "-o", default="config.yaml", help="Output file path")
def config_init(output: str) -> None:
    """Initialize a new configuration file."""
    from pathlib import Path

    config_template = """# LM Cloud Sync Configuration
# See: https://github.com/ryanmat/lm-cloud-sync

# LogicMonitor settings
logicmonitor:
  company: "your-company"  # Your LM portal name
  # Credentials are read from environment variables:
  # LM_BEARER_TOKEN or LM_ACCESS_ID + LM_ACCESS_KEY

# GCP Configuration
gcp:
  enabled: true
  # service_account_key_path: "/path/to/key.json"
  # Or set GOOGLE_APPLICATION_CREDENTIALS or GCP_SA_KEY_PATH env var

  filters:
    include_patterns: []      # e.g., ["prod-*", "staging-*"]
    exclude_patterns: []      # e.g., ["test-*", "sys-*"]
    exclude_resources: []     # Specific project IDs to exclude
    required_tags: {}         # e.g., {"managed": "true"}
    excluded_tags: {}         # e.g., {"ignore": "true"}

  regions:
    - us-central1
    - us-east1

  services:
    - COMPUTEENGINE
    - CLOUDSQL

# AWS Configuration
aws:
  enabled: false
  role_name: "LogicMonitorRole"  # IAM role name to assume in each account
  # Requires: organizations:ListAccounts permission on management account
  # And: IAM role with LM trust policy in each target account

  filters:
    include_patterns: []      # e.g., ["prod-*", "staging-*"]
    exclude_patterns: []      # e.g., ["sandbox-*"]
    exclude_resources: []     # Specific account IDs to exclude

  regions:
    - us-east-1
    - us-west-2

  services:
    - EC2
    - RDS
    - S3

# Azure Configuration
azure:
  enabled: false
  # tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  # client_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  # Or set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET env vars

  filters:
    include_patterns: []      # e.g., ["prod-*", "staging-*"]
    exclude_patterns: []      # e.g., ["sandbox-*"]
    exclude_resources: []     # Specific subscription IDs to exclude

  regions:
    - eastus
    - westus2

  services:
    - VIRTUALMACHINE
    - SQLDATABASE

# Sync behavior
sync:
  dry_run: false
  auto_discover: false
  create_missing: true
  update_existing: false
  delete_orphans: false
  group_name_template: "{provider} - {resource_id}"
  custom_properties:
    "lm.cloud.managed_by": "lm-cloud-sync"
    # lm.cloud.version is set automatically
"""
    output_path = Path(output)
    if output_path.exists():
        console.print(f"[red]File already exists: {output}[/red]")
        raise SystemExit(1)

    output_path.write_text(config_template)
    console.print(f"[green]Created configuration file: {output}[/green]")
    console.print("\nNext steps:")
    console.print("1. Edit the config file with your settings")
    console.print("2. Set environment variables:")
    console.print("   export LM_COMPANY=your-company")
    console.print("   export LM_BEARER_TOKEN=your-token")
    console.print("   export GCP_SA_KEY_PATH=/path/to/key.json")
    console.print("3. Run: lm-cloud-sync gcp discover")


@config.command("validate")
@click.option("--config", "-c", "config_path", default="config.yaml", help="Config file path")
def config_validate(config_path: str) -> None:
    """Validate a configuration file."""
    from pathlib import Path

    from lm_cloud_sync.core.config import Settings
    from lm_cloud_sync.core.exceptions import ConfigurationError

    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        raise SystemExit(1)

    try:
        settings = Settings.from_yaml(path)
        console.print("[green]Configuration is valid![/green]")
        console.print(f"\nLogicMonitor Company: {settings.logicmonitor.company}")
        console.print(f"GCP Enabled: {settings.gcp.enabled}")
        console.print(f"AWS Enabled: {settings.aws.enabled}")
        console.print(f"Azure Enabled: {settings.azure.enabled}")
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
