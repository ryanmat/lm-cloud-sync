#!/usr/bin/env python3
# Description: Delete AWS integration from LogicMonitor via Terraform provisioner.
# Description: Handles group deletion with structured error reporting and correct exit codes.

"""Delete AWS integration from LogicMonitor.

This script is called by Terraform to delete AWS device groups.
It uses the lm-cloud-sync library to interact with the LogicMonitor API.
"""

import argparse
import os
import sys

# Try to import from installed package first, then fall back to local src
try:
    from pydantic import SecretStr

    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.providers.aws.groups import delete_aws_group, get_group_by_account_id
except ImportError:
    # Add src to path for local development
    src_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")
    sys.path.insert(0, src_path)
    from pydantic import SecretStr

    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.providers.aws.groups import delete_aws_group, get_group_by_account_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete AWS integration from LogicMonitor")
    parser.add_argument("--account-id", required=True, help="AWS account ID")
    args = parser.parse_args()

    # Get credentials from environment
    company = os.environ.get("LM_COMPANY")
    bearer_token = os.environ.get("LM_BEARER_TOKEN")

    if not company or not bearer_token:
        print("Error: LM_COMPANY and LM_BEARER_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    client = LogicMonitorClient(company=company, bearer_token=SecretStr(bearer_token))

    try:
        group = get_group_by_account_id(client, args.account_id)

        if not group:
            print(f"No group found for AWS account {args.account_id}")
            return

        if group.id:
            delete_aws_group(client, group.id)
            print(f"Deleted AWS integration for account {args.account_id} (group ID: {group.id})")
        else:
            print(
                f"Cannot delete: group ID not found for account {args.account_id}",
                file=sys.stderr,
            )
            sys.exit(1)
    except Exception as e:
        print(f"Error deleting group for account {args.account_id}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
