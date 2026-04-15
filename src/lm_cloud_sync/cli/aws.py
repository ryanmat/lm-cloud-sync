# Description: AWS CLI commands for lm-cloud-sync.
# Description: Provides discover, status, sync, and delete commands for AWS accounts.

import json
import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from lm_cloud_sync.cli.helpers import get_lm_client, get_settings
from lm_cloud_sync.core.exceptions import LMCloudSyncError
from lm_cloud_sync.core.resync import list_cloud_root_groups, resync_group

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def aws(ctx: click.Context) -> None:
    """AWS account management.

    Discover and sync AWS accounts to LogicMonitor.
    """
    pass


@aws.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option(
    "--auto-discover",
    is_flag=True,
    default=True,
    help="Use AWS Organizations API to discover accounts (required)",
)
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def discover(
    ctx: click.Context,
    config_path: str | None,
    auto_discover: bool,
    output: str,
) -> None:
    """Discover AWS accounts.

    Lists all AWS accounts in your organization.
    Requires --auto-discover flag and organizations:ListAccounts permission.

    \b
    Examples:
        lm-cloud-sync aws discover --auto-discover
        lm-cloud-sync aws discover --auto-discover --output json
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.aws import AWSProvider

        provider = AWSProvider(config=settings.aws)

        with console.status("[bold green]Discovering AWS accounts..."):
            accounts = provider.discover(auto_discover=auto_discover)

        if output == "json":
            data = [
                {
                    "account_id": a.resource_id,
                    "display_name": a.display_name,
                    "status": a.status,
                    "email": getattr(a, "email", None),
                }
                for a in accounts
            ]
            console.print_json(json.dumps(data, indent=2))
        else:
            if not accounts:
                console.print("[yellow]No accounts found[/yellow]")
                return

            table = Table(title=f"AWS Accounts ({len(accounts)} found)")
            table.add_column("Account ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Email", style="blue")
            table.add_column("Status", style="yellow")

            for account in accounts:
                table.add_row(
                    account.resource_id,
                    account.display_name,
                    getattr(account, "email", "") or "",
                    account.status,
                )

            console.print(table)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during discovery")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@aws.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--show-orphans", is_flag=True, help="Show orphaned integrations")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def status(
    ctx: click.Context,
    config_path: str | None,
    show_orphans: bool,
    output: str,
) -> None:
    """Show AWS sync status.

    Compares AWS accounts with existing LogicMonitor integrations.

    \b
    Examples:
        lm-cloud-sync aws status
        lm-cloud-sync aws status --show-orphans
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.aws import AWSProvider

        provider = AWSProvider(config=settings.aws)

        with console.status("[bold green]Fetching status..."):
            accounts = provider.discover(auto_discover=True)
            account_ids = {a.resource_id for a in accounts}

            with get_lm_client(settings) as client:
                integrations = provider.list_integrations(client)
            integration_ids = {g.resource_id for g in integrations}

        synced = account_ids & integration_ids
        missing = account_ids - integration_ids
        orphaned = integration_ids - account_ids

        if output == "json":
            data = {
                "total_accounts": len(accounts),
                "total_integrations": len(integrations),
                "synced": sorted(list(synced)),
                "missing": sorted(list(missing)),
                "orphaned": sorted(list(orphaned)) if show_orphans else [],
            }
            console.print_json(json.dumps(data, indent=2))
        else:
            console.print("\n[bold]Sync Status[/bold]")
            console.print(f"  AWS Accounts:      {len(accounts)}")
            console.print(f"  LM Integrations:   {len(integrations)}")
            console.print(f"  [green]Synced:[/green]           {len(synced)}")
            console.print(f"  [yellow]Missing:[/yellow]          {len(missing)}")
            if show_orphans:
                console.print(f"  [red]Orphaned:[/red]         {len(orphaned)}")

            if missing:
                console.print("\n[yellow]Missing integrations (not in LM):[/yellow]")
                for aid in sorted(missing):
                    console.print(f"  - {aid}")

            if show_orphans and orphaned:
                console.print("\n[red]Orphaned integrations (not in AWS):[/red]")
                for aid in sorted(orphaned):
                    console.print(f"  - {aid}")

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during status check")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@aws.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option(
    "--auto-discover",
    is_flag=True,
    default=True,
    help="Use AWS Organizations API to discover accounts (required)",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--delete-orphans", is_flag=True, help="Delete orphaned integrations")
@click.option("--parent-group-id", "-p", type=int, help="LogicMonitor parent group ID for new integrations")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def sync(
    ctx: click.Context,
    config_path: str | None,
    auto_discover: bool,
    dry_run: bool,
    delete_orphans: bool,
    parent_group_id: int | None,
    yes: bool,
) -> None:
    """Sync AWS accounts to LogicMonitor.

    Creates LogicMonitor integrations for AWS accounts.
    Requires --auto-discover flag and appropriate AWS/LM permissions.

    \b
    Prerequisites:
    1. AWS credentials with organizations:ListAccounts permission
    2. IAM role (LogicMonitorRole) created in each target account
    3. LogicMonitor Bearer token

    \b
    Examples:
        lm-cloud-sync aws sync --auto-discover --dry-run
        lm-cloud-sync aws sync --auto-discover --yes
        lm-cloud-sync aws sync --auto-discover --parent-group-id 123 --yes
        lm-cloud-sync aws sync --auto-discover --delete-orphans --yes
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.aws import AWSProvider

        provider = AWSProvider(config=settings.aws)

        # Get parent group ID (CLI flag takes precedence)
        parent_id = parent_group_id or settings.aws.parent_group_id or settings.logicmonitor.parent_group_id

        if dry_run:
            console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")

        # Discover accounts
        with console.status("[bold green]Discovering AWS accounts..."):
            accounts = provider.discover(auto_discover=auto_discover)

        console.print(f"Found [bold]{len(accounts)}[/bold] AWS accounts")

        # Get existing integrations
        with console.status("[bold green]Fetching existing integrations..."):
            with get_lm_client(settings) as client:
                integrations = provider.list_integrations(client)

        existing_ids = {g.resource_id for g in integrations}
        account_ids = {a.resource_id for a in accounts}

        # Calculate changes
        to_create = [a for a in accounts if a.resource_id not in existing_ids]
        to_skip = [a for a in accounts if a.resource_id in existing_ids]
        orphans = [g for g in integrations if g.resource_id not in account_ids]

        console.print(f"  To create: [green]{len(to_create)}[/green]")
        console.print(f"  Already exists: [yellow]{len(to_skip)}[/yellow]")
        if orphans:
            console.print(f"  Orphaned: [red]{len(orphans)}[/red]")

        if to_create:
            console.print("\n[bold]Accounts to integrate:[/bold]")
            for account in to_create:
                console.print(f"  - {account.resource_id} ({account.display_name})")

        if orphans and delete_orphans:
            console.print("\n[bold red]Integrations to delete:[/bold red]")
            for group in orphans:
                console.print(f"  - {group.resource_id} (LM Group ID: {group.id})")

        if not to_create and not (orphans and delete_orphans):
            console.print("\n[green]Nothing to do - all accounts are in sync[/green]")
            return

        # Confirm unless --yes or --dry-run
        if not dry_run and not yes and not click.confirm("\nProceed with sync?"):
            console.print("[yellow]Aborted[/yellow]")
            return

        # Execute sync
        if dry_run:
            console.print("\n[yellow]DRY RUN - Would have made the following changes:[/yellow]")
            for account in to_create:
                console.print(f"  [green]CREATE[/green] AWS - {account.resource_id}")
            if orphans and delete_orphans:
                for group in orphans:
                    console.print(f"  [red]DELETE[/red] {group.name} (ID: {group.id})")
        else:
            with get_lm_client(settings) as client:
                result = provider.sync(
                    client=client,
                    dry_run=False,
                    auto_discover=auto_discover,
                    create_missing=True,
                    delete_orphans=delete_orphans,
                    parent_id=parent_id,
                    name_template=settings.sync.group_name_template,
                    custom_properties=settings.sync.custom_properties,
                )

                console.print("\n[bold]Sync Results:[/bold]")
                console.print(f"  Created: [green]{len(result.created)}[/green]")
                console.print(f"  Skipped: [yellow]{len(result.skipped)}[/yellow]")
                if result.deleted:
                    console.print(f"  Deleted: [red]{len(result.deleted)}[/red]")
                if result.failed:
                    console.print(f"  Failed: [red]{len(result.failed)}[/red]")
                    for resource_id, error in result.failed.items():
                        console.print(f"    - {resource_id}: {error}")

                if result.has_failures:
                    sys.exit(1)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during sync")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@aws.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--account-id", required=True, help="AWS account ID to delete integration for")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(
    ctx: click.Context,
    config_path: str | None,
    account_id: str,
    yes: bool,
) -> None:
    """Delete an AWS integration from LogicMonitor.

    \b
    Examples:
        lm-cloud-sync aws delete --account-id 123456789012
        lm-cloud-sync aws delete --account-id 123456789012 --yes
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.aws import AWSProvider

        provider = AWSProvider(config=settings.aws)

        with get_lm_client(settings) as client:
            integrations = provider.list_integrations(client)

            # Find the integration
            target = None
            for group in integrations:
                if group.resource_id == account_id:
                    target = group
                    break

            if not target:
                console.print(
                    f"[yellow]No integration found for AWS account {account_id}[/yellow]"
                )
                sys.exit(1)

            console.print(f"Found integration: {target.name} (ID: {target.id})")

            if not yes and not click.confirm("Delete this integration?"):
                console.print("[yellow]Aborted[/yellow]")
                return

            if target.id:
                provider.delete_integration(client, target.id)
                console.print(f"[green]Deleted integration for account {account_id}[/green]")
            else:
                console.print("[red]Cannot delete: group ID not found[/red]")
                sys.exit(1)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during delete")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@aws.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--group-id", type=int, help="Specific LM group ID to resync")
@click.option("--all", "resync_all", is_flag=True, help="Resync all AWS cloud root groups")
@click.option("--extra-json", help="JSON string to merge into the extra field")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def resync(
    ctx: click.Context,
    config_path: str | None,
    group_id: int | None,
    resync_all: bool,
    extra_json: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Resync AWS cloud integrations to trigger the LM sync engine.

    Performs a full PUT on cloud root groups to trigger credential validation,
    region re-evaluation, and service re-discovery.

    \b
    Examples:
        lm-cloud-sync aws resync --all --dry-run
        lm-cloud-sync aws resync --group-id 1870
        lm-cloud-sync aws resync --all --extra-json '{"default": {"monitoringRegions": ["us-east-1"]}}'
    """
    if not group_id and not resync_all:
        console.print("[red]Error: specify --group-id or --all[/red]")
        sys.exit(1)

    extra_modifications = None
    if extra_json:
        try:
            extra_modifications = json.loads(extra_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON in --extra-json: {e}[/red]")
            sys.exit(1)

    try:
        settings = get_settings(config_path)

        with get_lm_client(settings) as client:
            if group_id:
                target_groups = [{"id": group_id, "name": f"Group {group_id}", "groupType": "AWS/AwsRoot"}]
            else:
                with console.status("[bold green]Listing AWS cloud root groups..."):
                    target_groups = list_cloud_root_groups(client, provider="aws")

            if not target_groups:
                console.print("[yellow]No AWS cloud root groups found[/yellow]")
                return

            if dry_run:
                console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")

            console.print(f"Found [bold]{len(target_groups)}[/bold] AWS cloud root group(s)")
            for g in target_groups:
                console.print(f"  - {g['name']} (ID: {g['id']})")

            if not dry_run and not yes and not click.confirm("\nResync these groups?"):
                console.print("[yellow]Aborted[/yellow]")
                return

            table = Table(title="Resync Results")
            table.add_column("Group ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Test Result", style="blue")
            table.add_column("Warnings", style="red")

            results = []
            for group in target_groups:
                result = resync_group(
                    client,
                    group_id=group["id"],
                    extra_modifications=extra_modifications,
                    dry_run=dry_run,
                )
                results.append(result)

                warnings = ""
                if result.masked_fields:
                    warnings = f"Masked: {', '.join(result.masked_fields)}"
                if result.error:
                    warnings = f"{warnings}; {result.error}" if warnings else result.error

                test_result_str = ""
                if result.test_results:
                    test_result_str = "; ".join(
                        f"{k}: {v}" for k, v in result.test_results.items()
                    )

                status_style = {
                    "success": "[green]success[/green]",
                    "dry_run": "[yellow]dry_run[/yellow]",
                    "failed": "[red]failed[/red]",
                }.get(result.status, result.status)

                table.add_row(
                    str(result.group_id),
                    result.group_name,
                    status_style,
                    test_result_str or "-",
                    warnings or "-",
                )

            console.print()
            console.print(table)

            if any(r.status == "failed" for r in results):
                sys.exit(1)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during resync")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)
