# Description: AWS-only integration example for lm-cloud-sync.
# Description: Shows inline account list and Organizations auto-discovery options.

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

provider "logicmonitor" {
  api_id  = var.lm_api_id
  api_key = var.lm_api_key
  company = var.lm_company
}

provider "aws" {
  # Uses default credential chain (env vars, ~/.aws/credentials, instance profile)
}

# Option 1: Define accounts inline
module "aws_integrations" {
  source = "../../modules/aws"

  lm_api_id          = var.lm_api_id
  lm_api_key         = var.lm_api_key
  lm_company         = var.lm_company
  lm_parent_group_id = var.lm_parent_group_id
  aws_role_name      = var.aws_role_name

  accounts = [
    {
      account_id   = "123456789012"
      display_name = "Production Account"
    },
    {
      account_id   = "234567890123"
      display_name = "Development Account"
    },
  ]
}

# Option 2: Auto-discover all accounts in the AWS Organization
# module "aws_auto_discover" {
#   source = "../../modules/aws"
#
#   lm_api_id     = var.lm_api_id
#   lm_api_key    = var.lm_api_key
#   lm_company    = var.lm_company
#   aws_role_name = var.aws_role_name
#
#   auto_discover       = true
#   exclude_account_ids = ["999999999999"]  # management account
# }

output "managed_accounts" {
  value = module.aws_integrations.managed_accounts
}

output "group_ids" {
  value = module.aws_integrations.group_ids
}

output "external_id" {
  description = "Use this external ID in your IAM role trust policies"
  value       = module.aws_integrations.external_id
}
