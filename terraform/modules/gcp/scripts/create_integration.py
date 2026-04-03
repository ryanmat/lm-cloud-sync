#!/usr/bin/env python3
"""Create a GCP integration in LogicMonitor.

Called by Terraform local-exec provisioner.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Try to import from installed package first, fall back to local development
try:
    from lm_cloud_sync.core.exceptions import GroupExistsError
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.core.models import CloudProvider, GCPProject
    from lm_cloud_sync.providers.gcp.groups import create_gcp_group
except ImportError:
    # For local development, add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
    from lm_cloud_sync.core.exceptions import GroupExistsError
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.core.models import CloudProvider, GCPProject
    from lm_cloud_sync.providers.gcp.groups import create_gcp_group

from pydantic import SecretStr


def main() -> None:
    """Create a GCP integration in LogicMonitor."""
    parser = argparse.ArgumentParser(
        description="Create a GCP integration in LogicMonitor"
    )
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    parser.add_argument("--display-name", required=True, help="Display name for group")
    parser.add_argument(
        "--parent-group-id", type=int, default=1, help="Parent group ID"
    )
    args = parser.parse_args()

    # Get credentials from environment
    token = os.environ.get("LM_BEARER_TOKEN")
    company = os.environ.get("LM_COMPANY")
    sa_key_path = os.environ.get("GCP_SA_KEY_PATH")

    if not all([token, company, sa_key_path]):
        print(
            "Missing required environment variables: LM_BEARER_TOKEN, LM_COMPANY, GCP_SA_KEY_PATH",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load service account key
    with Path(sa_key_path).open() as f:
        sa_key = json.load(f)

    # Create LM client
    client = LogicMonitorClient(
        company=company,
        bearer_token=SecretStr(token),
    )

    # Create project model
    project = GCPProject(
        resource_id=args.project_id,
        display_name=args.display_name,
        status="ACTIVE",
        project_number="0",  # Not needed for creation
    )

    try:
        result = create_gcp_group(
            client=client,
            resource=project,
            service_account_key=sa_key,
            parent_id=args.parent_group_id,
        )
        print(f"Created group {result.id} for {args.project_id}")
    except GroupExistsError:
        print(f"Group already exists for {args.project_id}")
    except Exception as e:
        print(f"Error creating group for {args.project_id}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
