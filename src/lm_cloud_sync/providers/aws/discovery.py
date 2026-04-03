# Description: AWS account discovery using Organizations API.
# Description: Discovers AWS accounts for LogicMonitor integration.

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError

from lm_cloud_sync.core.exceptions import DiscoveryError
from lm_cloud_sync.core.models import AWSAccount

if TYPE_CHECKING:
    from mypy_boto3_organizations import OrganizationsClient
    from mypy_boto3_sts import STSClient

logger = logging.getLogger(__name__)


class AWSAccountDiscovery:
    """Discovers AWS accounts using the Organizations API.

    Requires permissions:
    - organizations:ListAccounts (on management account)
    - organizations:DescribeOrganization (optional, for org info)
    """

    def __init__(
        self,
        organizations_client: OrganizationsClient | None = None,
        sts_client: STSClient | None = None,
    ) -> None:
        """Initialize AWS account discovery.

        Args:
            organizations_client: Boto3 Organizations client. If None, creates default.
            sts_client: Boto3 STS client for caller identity. If None, creates default.
        """
        self._org_client = organizations_client
        self._sts_client = sts_client

    @property
    def org_client(self) -> OrganizationsClient:
        """Get or create Organizations client."""
        if self._org_client is None:
            self._org_client = boto3.client("organizations")
        return self._org_client

    @property
    def sts_client(self) -> STSClient:
        """Get or create STS client."""
        if self._sts_client is None:
            self._sts_client = boto3.client("sts")
        return self._sts_client

    def get_caller_identity(self) -> dict:
        """Get the identity of the current AWS credentials.

        Returns:
            Dict with Account, Arn, and UserId.
        """
        return self.sts_client.get_caller_identity()

    def discover_accounts(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        exclude_accounts: list[str] | None = None,
        active_only: bool = True,
    ) -> list[AWSAccount]:
        """Discover AWS accounts in the organization.

        Args:
            include_patterns: Glob patterns for account names to include.
            exclude_patterns: Glob patterns for account names to exclude.
            exclude_accounts: Specific account IDs to exclude.
            active_only: Only return ACTIVE accounts (default True).

        Returns:
            List of AWSAccount objects.

        Raises:
            DiscoveryError: If account discovery fails.
        """
        try:
            accounts = self._list_all_accounts()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "AWSOrganizationsNotInUseException":
                raise DiscoveryError(
                    "AWS Organizations is not enabled for this account. "
                    "Use --accounts flag to specify accounts explicitly."
                ) from e
            elif error_code == "AccessDeniedException":
                raise DiscoveryError(
                    "Access denied to AWS Organizations API. "
                    "Ensure you have organizations:ListAccounts permission."
                ) from e
            raise DiscoveryError(f"Failed to list AWS accounts: {e}") from e

        # Filter accounts
        filtered = []
        for account in accounts:
            if active_only and account.status != "ACTIVE":
                continue

            if not self._matches_filters(
                account_id=account.resource_id,
                account_name=account.display_name,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                exclude_accounts=exclude_accounts,
            ):
                continue

            filtered.append(account)

        logger.info(f"Discovered {len(filtered)} AWS accounts (filtered from {len(accounts)})")
        return filtered

    def _list_all_accounts(self) -> list[AWSAccount]:
        """List all accounts using pagination."""
        accounts = []
        paginator = self.org_client.get_paginator("list_accounts")

        for page in paginator.paginate():
            for item in page.get("Accounts", []):
                account = AWSAccount(
                    resource_id=item["Id"],
                    display_name=item.get("Name", item["Id"]),
                    status=item.get("Status", "UNKNOWN"),
                    email=item.get("Email"),
                    arn=item.get("Arn"),
                    metadata={
                        "joined_method": item.get("JoinedMethod", ""),
                        "joined_timestamp": (
                            item["JoinedTimestamp"].isoformat()
                            if item.get("JoinedTimestamp")
                            else ""
                        ),
                    },
                )
                accounts.append(account)

        return accounts

    def _matches_filters(
        self,
        account_id: str,
        account_name: str,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        exclude_accounts: list[str] | None,
    ) -> bool:
        """Check if an account matches the filter criteria."""
        # Explicit exclusion by account ID
        if exclude_accounts and account_id in exclude_accounts:
            return False

        # Check include patterns (if specified, must match at least one)
        if include_patterns and not any(
            fnmatch.fnmatch(account_name, p) or fnmatch.fnmatch(account_id, p)
            for p in include_patterns
        ):
            return False

        # Check exclude patterns
        return not (exclude_patterns and any(fnmatch.fnmatch(account_name, p) or fnmatch.fnmatch(account_id, p) for p in exclude_patterns))
