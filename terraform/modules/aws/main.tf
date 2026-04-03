# LogicMonitor AWS Integration Module
#
# Creates LogicMonitor device groups for AWS accounts using lm-cloud-sync.
#
# Prerequisites:
# 1. lm-cloud-sync installed (pip install lm-cloud-sync)
# 2. IAM role created in each target AWS account with LM trust policy
# 3. LogicMonitor Bearer token with API access

terraform {
  required_version = ">= 1.0"
}

locals {
  # Load accounts from YAML file if provided, otherwise use inline list
  accounts_from_file = var.accounts_file != "" ? yamldecode(file(var.accounts_file))["accounts"] : []

  # Combine accounts from both sources
  all_accounts = length(var.accounts) > 0 ? var.accounts : local.accounts_from_file

  # Convert to map for for_each
  accounts = { for account in local.all_accounts : account.account_id => account }
}

# Create AWS integration for each account
resource "null_resource" "aws_integration" {
  for_each = local.accounts

  triggers = {
    account_id         = each.key
    display_name       = lookup(each.value, "display_name", each.key)
    role_name          = var.aws_role_name
    lm_bearer_token    = var.lm_bearer_token
    lm_company         = var.lm_company
    python_command     = var.python_command
    script_delete_path = "${path.module}/scripts/delete_integration.py"
  }

  provisioner "local-exec" {
    command = <<-EOT
      ${var.python_command} ${path.module}/scripts/create_integration.py \
        --account-id "${each.key}" \
        --display-name "${lookup(each.value, "display_name", each.key)}" \
        --role-name "${var.aws_role_name}" \
        --parent-group-id ${var.lm_parent_group_id}
    EOT

    environment = {
      LM_BEARER_TOKEN = var.lm_bearer_token
      LM_COMPANY      = var.lm_company
    }
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      ${self.triggers.python_command} ${self.triggers.script_delete_path} \
        --account-id "${self.triggers.account_id}"
    EOT

    environment = {
      LM_BEARER_TOKEN = self.triggers.lm_bearer_token
      LM_COMPANY      = self.triggers.lm_company
    }

    on_failure = continue
  }
}

# Helper to run lm-cloud-sync discover for auto-discovery
resource "null_resource" "discover_accounts" {
  count = var.auto_discover ? 1 : 0

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "lm-cloud-sync aws discover --auto-discover --output json > ${path.module}/discovered_accounts.json"
  }
}
