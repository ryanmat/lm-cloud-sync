# Description: GCP-only integration example for lm-cloud-sync.
# Description: Shows inline project list and org-wide auto-discovery options.

terraform {
  required_version = ">= 1.0"

  required_providers {
    logicmonitor = {
      source  = "ryanmat/logicmonitor"
      version = ">= 1.0"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "logicmonitor" {
  api_id  = var.lm_api_id
  api_key = var.lm_api_key
  company = var.lm_company
}

# Option 1: Define projects inline
module "gcp_integrations" {
  source = "../../modules/gcp"

  lm_api_id                    = var.lm_api_id
  lm_api_key                   = var.lm_api_key
  lm_company                   = var.lm_company
  lm_parent_group_id           = var.lm_parent_group_id
  gcp_service_account_key_path = var.gcp_service_account_key_path

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
}

# Option 2: Auto-discover all projects in a GCP organization
# module "gcp_auto_discover" {
#   source = "../../modules/gcp"
#
#   lm_api_id                    = var.lm_api_id
#   lm_api_key                   = var.lm_api_key
#   lm_company                   = var.lm_company
#   gcp_service_account_key_path = var.gcp_service_account_key_path
#
#   gcp_org_id          = "123456789012"
#   exclude_project_ids = ["sandbox-project", "test-project"]
# }

output "managed_projects" {
  value = module.gcp_integrations.managed_projects
}

output "group_ids" {
  value = module.gcp_integrations.group_ids
}
