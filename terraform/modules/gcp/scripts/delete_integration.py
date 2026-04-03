#!/usr/bin/env python3
"""Delete a GCP integration from LogicMonitor.

Called by Terraform local-exec provisioner on destroy.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Try to import from installed package first, fall back to local development
try:
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.providers.gcp.groups import get_group_by_project_id
except ImportError:
    # For local development, add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.providers.gcp.groups import get_group_by_project_id

from pydantic import SecretStr


def main() -> None:
    """Delete a GCP integration from LogicMonitor."""
    parser = argparse.ArgumentParser(
        description="Delete a GCP integration from LogicMonitor"
    )
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    args = parser.parse_args()

    # Get credentials from environment
    token = os.environ.get("LM_BEARER_TOKEN")
    company = os.environ.get("LM_COMPANY")

    if not all([token, company]):
        print(
            "Missing required environment variables: LM_BEARER_TOKEN, LM_COMPANY",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create LM client
    client = LogicMonitorClient(
        company=company,
        bearer_token=SecretStr(token),
    )

    try:
        group = get_group_by_project_id(client, args.project_id)
        if group:
            client.delete(f"device/groups/{group.id}")
            print(f"Deleted group {group.id} for {args.project_id}")
        else:
            print(f"No group found for {args.project_id}")
    except Exception as e:
        print(f"Error deleting group for {args.project_id}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
