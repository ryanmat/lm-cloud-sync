# Description: GCP LM Cloud Sync Terraform module.
# Description: Creates LogicMonitor device groups for GCP projects using the ryanmat/logicmonitor provider.

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

# Auto-discover all active projects in the GCP organization.
# Only runs when gcp_org_id is set. When not set, uses static project list.
data "google_projects" "org" {
  count  = var.gcp_org_id != "" ? 1 : 0
  filter = "parent.id:${var.gcp_org_id} lifecycleState:ACTIVE"
}

# Create an LM device group for each GCP project
resource "logicmonitor_device_group" "gcp_project" {
  for_each = local.projects

  name        = replace(replace(var.group_name_template, "{project_id}", each.key), "{display_name}", lookup(each.value, "display_name", each.key))
  parent_id   = var.lm_parent_group_id
  description = lookup(each.value, "display_name", each.key)
  group_type  = "GCP/GcpRoot"

  custom_properties = local.custom_props

  extra = jsonencode({
    account = {
      projectId         = each.key
      collectorId       = -2
      schedule          = var.schedule
      serviceAccountKey = local.sa_key
    }
    default  = local.default_config
    services = local.service_config
  })
}
