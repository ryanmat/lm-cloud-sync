# Description: AWS LM Cloud Sync Terraform module.
# Description: Creates LogicMonitor device groups for AWS accounts using the ryanmat/logicmonitor provider.

terraform {
  required_version = ">= 1.0"

  required_providers {
    logicmonitor = {
      source  = "ryanmat/logicmonitor"
      version = ">= 1.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Auto-discover all accounts in the AWS Organization.
# Only runs when auto_discover is true. Requires organizations:ListAccounts permission.
data "aws_organizations_organization" "org" {
  count = var.auto_discover ? 1 : 0
}

# Get the LM external ID for cross-account IAM role assumption
data "logicmonitor_aws_external_id" "this" {}

# Create an LM device group for each AWS account
resource "logicmonitor_device_group" "aws_account" {
  for_each = local.accounts

  name        = replace(replace(var.group_name_template, "{account_id}", each.key), "{display_name}", lookup(each.value, "display_name", each.key))
  parent_id   = var.lm_parent_group_id
  description = lookup(each.value, "display_name", each.key)
  group_type  = "AWS/AwsRoot"

  custom_properties = local.custom_props

  extra = jsonencode({
    account = {
      assumedRoleArn = "arn:aws:iam::${each.key}:role/${var.aws_role_name}"
      externalId     = data.logicmonitor_aws_external_id.this.external_id
      collectorId    = -2
      schedule       = var.schedule
    }
    default  = local.default_config
    services = local.service_config
  })
}
