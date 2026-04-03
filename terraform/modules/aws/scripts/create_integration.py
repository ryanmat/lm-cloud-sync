#!/usr/bin/env python3
# Description: Create AWS integration in LogicMonitor via Terraform provisioner.
# Description: Handles group creation with idempotency and structured error reporting.

"""Create AWS integration in LogicMonitor.

This script is called by Terraform to create AWS device groups.
It uses the lm-cloud-sync library to interact with the LogicMonitor API.
"""

import argparse
import os
import sys

# Try to import from installed package first, then fall back to local src
try:
    from pydantic import SecretStr

    from lm_cloud_sync.core.exceptions import GroupExistsError
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.core.models import AWSAccount
    from lm_cloud_sync.providers.aws.auth import build_role_arn, get_external_id
    from lm_cloud_sync.providers.aws.groups import create_aws_group, get_group_by_account_id
except ImportError:
    # Add src to path for local development
    src_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")
    sys.path.insert(0, src_path)
    from pydantic import SecretStr

    from lm_cloud_sync.core.exceptions import GroupExistsError
    from lm_cloud_sync.core.lm_client import LogicMonitorClient
    from lm_cloud_sync.core.models import AWSAccount
    from lm_cloud_sync.providers.aws.auth import build_role_arn, get_external_id
    from lm_cloud_sync.providers.aws.groups import create_aws_group, get_group_by_account_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Create AWS integration in LogicMonitor")
    parser.add_argument("--account-id", required=True, help="AWS account ID")
    parser.add_argument("--display-name", required=True, help="Display name for the account")
    parser.add_argument("--role-name", default="LogicMonitorRole", help="IAM role name")
    parser.add_argument("--parent-group-id", type=int, default=1, help="Parent group ID")
    args = parser.parse_args()

    # Get credentials from environment
    company = os.environ.get("LM_COMPANY")
    bearer_token = os.environ.get("LM_BEARER_TOKEN")

    if not company or not bearer_token:
        print("Error: LM_COMPANY and LM_BEARER_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    client = LogicMonitorClient(company=company, bearer_token=SecretStr(bearer_token))

    try:
        existing = get_group_by_account_id(client, args.account_id)
        if existing:
            print(f"Group already exists for account {args.account_id}: {existing.name}")
            return

        # Get external ID from LM
        external_id = get_external_id(client)

        # Build role ARN
        role_arn = build_role_arn(args.account_id, args.role_name)

        # Create account resource
        account = AWSAccount(
            resource_id=args.account_id,
            display_name=args.display_name,
            status="ACTIVE",
        )

        # Create the group
        group = create_aws_group(
            client=client,
            resource=account,
            assumed_role_arn=role_arn,
            external_id=external_id,
            parent_id=args.parent_group_id,
            name_template="AWS - {display_name}",
        )

        print(f"Created AWS integration: {group.name} (ID: {group.id})")
    except GroupExistsError:
        print(f"Group already exists for account {args.account_id}")
    except Exception as e:
        print(f"Error creating group for account {args.account_id}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
