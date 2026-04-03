# Example: GCP-only integration with lm-cloud-sync
#
# This example shows how to use the GCP module to create
# LogicMonitor integrations for GCP projects.

terraform {
  required_version = ">= 1.0"
}

# Option 1: Define projects inline
module "gcp_integrations" {
  source = "../../modules/gcp"

  lm_company                   = var.lm_company
  lm_bearer_token              = var.lm_bearer_token
  lm_parent_group_id           = var.lm_parent_group_id
  gcp_service_account_key_path = var.gcp_service_account_key_path

  # Define projects inline
  projects = [
    {
      project_id   = "my-project-1"
      display_name = "My Project 1"
    },
    {
      project_id   = "my-project-2"
      display_name = "My Project 2"
    },
  ]

  # Or load from YAML file:
  # projects_file = "${path.module}/projects.yaml"
}

output "managed_projects" {
  value = module.gcp_integrations.managed_projects
}
