# LM Cloud Sync - GCP Terraform Module
# Creates LogicMonitor GCP device groups for specified projects

terraform {
  required_version = ">= 1.0"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.0"
    }
  }
}

locals {
  # Load projects from YAML file if provided, otherwise use projects variable
  projects_from_file = var.projects_file != "" ? yamldecode(file(var.projects_file)).projects : []
  projects_list      = length(var.projects) > 0 ? var.projects : local.projects_from_file
  projects           = { for p in local.projects_list : p.project_id => p }
}

# Create GCP integrations using Python script
resource "null_resource" "gcp_integration" {
  for_each = local.projects

  triggers = {
    project_id      = each.key
    display_name    = lookup(each.value, "display_name", each.key)
    # Store for destroy provisioner
    lm_bearer_token = var.lm_bearer_token
    lm_company      = var.lm_company
    python_command  = var.python_command
    script_path     = "${path.module}/scripts/delete_integration.py"
  }

  provisioner "local-exec" {
    command = <<-EOT
      ${var.python_command} ${path.module}/scripts/create_integration.py \
        --project-id "${each.key}" \
        --display-name "${lookup(each.value, "display_name", each.key)}" \
        --parent-group-id ${var.lm_parent_group_id}
    EOT

    environment = {
      LM_BEARER_TOKEN = var.lm_bearer_token
      LM_COMPANY      = var.lm_company
      GCP_SA_KEY_PATH = var.gcp_service_account_key_path
    }
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      ${self.triggers.python_command} ${self.triggers.script_path} \
        --project-id "${self.triggers.project_id}"
    EOT

    environment = {
      LM_BEARER_TOKEN = self.triggers.lm_bearer_token
      LM_COMPANY      = self.triggers.lm_company
    }

    on_failure = continue
  }
}
