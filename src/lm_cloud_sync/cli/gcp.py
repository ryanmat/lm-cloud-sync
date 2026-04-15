# Description: GCP CLI commands for lm-cloud-sync.
# Description: Provides discover, status, sync, and delete commands for GCP projects.

"""GCP CLI commands for lm-cloud-sync."""

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
def gcp(ctx: click.Context) -> None:
    """GCP project management.

    Discover and sync GCP projects to LogicMonitor.
    """
    pass


@gcp.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--auto-discover", is_flag=True, help="Use organization-level discovery")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def discover(
    ctx: click.Context,
    config_path: str | None,
    auto_discover: bool,
    output: str,
) -> None:
    """Discover GCP projects.

    Lists all GCP projects accessible to the service account.

    \b
    Examples:
        lm-cloud-sync gcp discover
        lm-cloud-sync gcp discover --auto-discover
        lm-cloud-sync gcp discover --output json
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.gcp import GCPProvider

        provider = GCPProvider(config=settings.gcp)

        with console.status("[bold green]Discovering GCP projects..."):
            projects = provider.discover(auto_discover=auto_discover)

        if output == "json":
            data = [
                {
                    "project_id": p.resource_id,
                    "display_name": p.display_name,
                    "status": p.status,
                }
                for p in projects
            ]
            console.print_json(json.dumps(data, indent=2))
        else:
            if not projects:
                console.print("[yellow]No projects found[/yellow]")
                return

            table = Table(title=f"GCP Projects ({len(projects)} found)")
            table.add_column("Project ID", style="cyan")
            table.add_column("Display Name", style="green")
            table.add_column("Status", style="yellow")

            for project in projects:
                table.add_row(project.resource_id, project.display_name, project.status)

            console.print(table)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during discovery")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@gcp.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--show-orphans", is_flag=True, help="Show orphaned LM groups")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def status(
    ctx: click.Context,
    config_path: str | None,
    show_orphans: bool,
    output: str,
) -> None:
    """Show sync status.

    Compares discovered GCP projects with existing LM integrations.

    \b
    Examples:
        lm-cloud-sync gcp status
        lm-cloud-sync gcp status --show-orphans
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.gcp import GCPProvider

        provider = GCPProvider(config=settings.gcp)

        with console.status("[bold green]Fetching status..."):
            # Discover projects
            projects = provider.discover()
            project_ids = {p.resource_id for p in projects}

            # Get existing integrations
            with get_lm_client(settings) as client:
                integrations = provider.list_integrations(client)
            integration_ids = {g.resource_id for g in integrations}

        # Calculate status
        synced = project_ids & integration_ids
        missing = project_ids - integration_ids
        orphaned = integration_ids - project_ids

        if output == "json":
            data = {
                "total_projects": len(projects),
                "total_integrations": len(integrations),
                "synced": list(synced),
                "missing": list(missing),
                "orphaned": list(orphaned) if show_orphans else [],
            }
            console.print_json(json.dumps(data, indent=2))
        else:
            console.print("\n[bold]Sync Status[/bold]")
            console.print(f"  GCP Projects:      {len(projects)}")
            console.print(f"  LM Integrations:   {len(integrations)}")
            console.print(f"  [green]Synced:[/green]           {len(synced)}")
            console.print(f"  [yellow]Missing:[/yellow]          {len(missing)}")
            if show_orphans:
                console.print(f"  [red]Orphaned:[/red]         {len(orphaned)}")

            if missing:
                console.print("\n[yellow]Missing integrations (not in LM):[/yellow]")
                for pid in sorted(missing):
                    console.print(f"  - {pid}")

            if show_orphans and orphaned:
                console.print("\n[red]Orphaned integrations (not in GCP):[/red]")
                for pid in sorted(orphaned):
                    console.print(f"  - {pid}")

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during status check")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@gcp.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--auto-discover", is_flag=True, help="Use organization-level discovery")
@click.option("--delete-orphans", is_flag=True, help="Delete orphaned LM groups")
@click.option("--parent-group-id", "-p", type=int, help="LogicMonitor parent group ID for new integrations")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def sync(
    ctx: click.Context,
    config_path: str | None,
    dry_run: bool,
    auto_discover: bool,
    delete_orphans: bool,
    parent_group_id: int | None,
    yes: bool,
) -> None:
    """Sync GCP projects to LogicMonitor.

    Creates LM integrations for discovered GCP projects.

    \b
    Examples:
        lm-cloud-sync gcp sync --dry-run
        lm-cloud-sync gcp sync --yes
        lm-cloud-sync gcp sync --parent-group-id 123 --yes
        lm-cloud-sync gcp sync --delete-orphans --yes
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.gcp import GCPProvider

        provider = GCPProvider(config=settings.gcp)

        # Get parent group ID (CLI flag takes precedence)
        parent_id = parent_group_id or settings.gcp.parent_group_id or settings.logicmonitor.parent_group_id

        # Preview what will happen
        with console.status("[bold green]Analyzing sync..."):
            projects = provider.discover(auto_discover=auto_discover)
            project_ids = {p.resource_id for p in projects}

            with get_lm_client(settings) as client:
                integrations = provider.list_integrations(client)
            integration_ids = {g.resource_id for g in integrations}

        missing = project_ids - integration_ids
        orphaned = integration_ids - project_ids

        if dry_run:
            console.print("[bold yellow]DRY RUN - No changes will be made[/bold yellow]\n")

        console.print(f"Projects to create: {len(missing)}")
        if delete_orphans:
            console.print(f"Orphans to delete:  {len(orphaned)}")

        if not missing and not (delete_orphans and orphaned):
            console.print("\n[green]Nothing to do - all projects are synced![/green]")
            return

        # Show what will be created
        if missing:
            console.print("\n[green]Will create:[/green]")
            for pid in sorted(missing):
                console.print(f"  + {pid}")

        if delete_orphans and orphaned:
            console.print("\n[red]Will delete:[/red]")
            for pid in sorted(orphaned):
                console.print(f"  - {pid}")

        # Confirm unless --yes or --dry-run
        if not dry_run and not yes and not click.confirm("\nProceed with sync?"):
            console.print("[yellow]Aborted[/yellow]")
            return

        # Execute sync
        if dry_run:
            console.print("\n[bold yellow]DRY RUN - Would make the following changes:[/bold yellow]")
            for pid in sorted(missing):
                console.print(f"  [green]CREATE[/green] GCP - {pid}")
            if delete_orphans and orphaned:
                for pid in sorted(orphaned):
                    console.print(f"  [red]DELETE[/red] GCP - {pid}")
            return

        with console.status("[bold green]Syncing..."), get_lm_client(settings) as client:
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

        # Report results
        console.print("\n[bold]Sync Results[/bold]")
        console.print(f"  [green]Created:[/green]  {len(result.created)}")
        console.print(f"  [blue]Skipped:[/blue]  {len(result.skipped)}")
        if delete_orphans:
            console.print(f"  [red]Deleted:[/red]  {len(result.deleted)}")
        if result.failed:
            console.print(f"  [red]Failed:[/red]   {len(result.failed)}")
            for pid, error in result.failed.items():
                console.print(f"    - {pid}: {error}")

        if result.has_failures:
            sys.exit(1)

    except LMCloudSyncError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during sync")
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@gcp.command()
@click.option("--project-id", required=True, help="GCP project ID to delete integration for")
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(
    ctx: click.Context,
    project_id: str,
    config_path: str | None,
    yes: bool,
) -> None:
    """Delete a GCP integration from LogicMonitor.

    \b
    Examples:
        lm-cloud-sync gcp delete --project-id my-project-id
        lm-cloud-sync gcp delete --project-id my-project-id --yes
    """
    try:
        settings = get_settings(config_path)
        from lm_cloud_sync.providers.gcp import GCPProvider

        provider = GCPProvider(config=settings.gcp)

        with get_lm_client(settings) as client:
            integrations = provider.list_integrations(client)
            target = None
            for g in integrations:
                if g.resource_id == project_id:
                    target = g
                    break

            if not target:
                console.print(f"[red]Integration not found for project: {project_id}[/red]")
                sys.exit(1)

            console.print(f"Found integration: {target.name} (ID: {target.id})")

            if not yes and not click.confirm("Delete this integration?"):
                console.print("[yellow]Aborted[/yellow]")
                return

            if target.id:
                provider.delete_integration(client, target.id)
                console.print(f"[green]Deleted integration for {project_id}[/green]")
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


@gcp.command()
@click.option("--config", "-c", "config_path", help="Path to config file")
@click.option("--group-id", type=int, help="Specific LM group ID to resync")
@click.option("--all", "resync_all", is_flag=True, help="Resync all GCP cloud root groups")
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
    """Resync GCP cloud integrations to trigger the LM sync engine.

    Performs a full PUT on cloud root groups to trigger credential validation,
    region re-evaluation, and service re-discovery.

    \b
    Examples:
        lm-cloud-sync gcp resync --all --dry-run
        lm-cloud-sync gcp resync --group-id 2584
        lm-cloud-sync gcp resync --all --extra-json '{"default": {"monitoringRegions": ["us-central1"]}}'
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
                target_groups = [{"id": group_id, "name": f"Group {group_id}", "groupType": "GCP/GcpRoot"}]
            else:
                with console.status("[bold green]Listing GCP cloud root groups..."):
                    target_groups = list_cloud_root_groups(client, provider="gcp")

            if not target_groups:
                console.print("[yellow]No GCP cloud root groups found[/yellow]")
                return

            if dry_run:
                console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")

            console.print(f"Found [bold]{len(target_groups)}[/bold] GCP cloud root group(s)")
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
