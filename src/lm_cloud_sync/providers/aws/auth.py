# Description: AWS authentication helpers for LogicMonitor integration.
# Description: Handles external ID retrieval and IAM role ARN construction.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lm_cloud_sync.core.exceptions import LMAPIError

if TYPE_CHECKING:
    from lm_cloud_sync.core.lm_client import LogicMonitorClient

logger = logging.getLogger(__name__)

# LogicMonitor's AWS account ID for cross-account trust policy
LM_AWS_ACCOUNT_ID = "282028653949"
LM_AWS_PRINCIPAL = f"arn:aws:iam::{LM_AWS_ACCOUNT_ID}:root"


def get_external_id(client: LogicMonitorClient) -> str:
    """Retrieve the external ID from LogicMonitor for AWS IAM role trust.

    The external ID is required when creating IAM cross-account roles
    for LogicMonitor AWS integrations. It is valid for 1 hour and must
    be used by the same user who retrieved it.

    Args:
        client: LogicMonitor API client.

    Returns:
        External ID string.

    Raises:
        LMAPIError: If the API request fails.
    """
    response = client.get("aws/externalId")
    external_id = response.get("externalId")

    if not external_id:
        raise LMAPIError("Failed to retrieve AWS external ID from LogicMonitor API", status_code=500)

    logger.debug("Retrieved AWS external ID successfully")
    return external_id


def build_role_arn(account_id: str, role_name: str = "LogicMonitorRole") -> str:
    """Build the IAM role ARN for a given AWS account.

    Args:
        account_id: AWS account ID (12 digits).
        role_name: Name of the IAM role (default: LogicMonitorRole).

    Returns:
        Full IAM role ARN.
    """
    return f"arn:aws:iam::{account_id}:role/{role_name}"


def get_trust_policy(external_id: str) -> dict:
    """Generate the IAM trust policy for LogicMonitor cross-account access.

    This policy should be attached to the IAM role in each AWS account
    that LogicMonitor will monitor.

    Args:
        external_id: External ID from LogicMonitor API.

    Returns:
        Trust policy document as a dictionary.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": LM_AWS_PRINCIPAL},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
            }
        ],
    }


def get_permissions_policy() -> dict:
    """Generate the recommended IAM permissions policy for LogicMonitor.

    This policy grants read-only access to AWS resources that LogicMonitor
    needs to monitor.

    Returns:
        Permissions policy document as a dictionary.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:Describe*",
                    "rds:Describe*",
                    "rds:ListTagsForResource",
                    "s3:GetBucket*",
                    "s3:ListBucket*",
                    "s3:ListAllMyBuckets",
                    "elasticloadbalancing:Describe*",
                    "autoscaling:Describe*",
                    "lambda:List*",
                    "lambda:GetFunction",
                    "dynamodb:Describe*",
                    "dynamodb:List*",
                    "sqs:GetQueueAttributes",
                    "sqs:ListQueues",
                    "sns:GetTopicAttributes",
                    "sns:ListTopics",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                    "logs:DescribeLogGroups",
                    "tag:GetResources",
                ],
                "Resource": "*",
            }
        ],
    }
