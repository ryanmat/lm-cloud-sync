# Description: Local values for the GCP LM Cloud Sync Terraform module.
# Description: Computes service config, merges project sources, and builds the extra JSON payload.

locals {
  # Service monitoring config -- identical structure per service
  service_config = {
    for svc in var.services : svc => {
      useDefault                    = true
      selectAll                     = false
      monitoringRegions             = var.regions
      tags                          = []
      nameFilter                    = []
      deadOperation                 = var.dead_operation
      disableTerminatedHostAlerting = var.disable_terminated_alerting
    }
  }

  # Default monitoring settings
  default_config = {
    useDefault                    = true
    selectAll                     = false
    monitoringRegions             = var.regions
    tags                          = []
    nameFilter                    = []
    deadOperation                 = var.dead_operation
    disableTerminatedHostAlerting = var.disable_terminated_alerting
  }

  # Service account key loaded from file
  sa_key = jsondecode(file(var.gcp_service_account_key_path))

  # Custom properties as list of {name, value} objects (LM API format)
  custom_props = [
    for k, v in var.custom_properties : { name = k, value = v }
  ]

  # Project sources: merge discovered + static + file
  projects_from_file = var.projects_file != "" ? yamldecode(file(var.projects_file)).projects : []
  static_list        = length(var.projects) > 0 ? var.projects : local.projects_from_file

  discovered_list = var.gcp_org_id != "" ? [
    for p in data.google_projects.org[0].projects : {
      project_id   = p.project_id
      display_name = p.name
    }
    if !contains(var.exclude_project_ids, p.project_id)
  ] : []

  # Merge: static entries override discovered (append after, last write wins on dedup)
  merged_list = concat(local.discovered_list, local.static_list)

  projects_grouped = {
    for p in local.merged_list : p.project_id => p...
  }

  # Final project map: keyed by project_id
  projects = {
    for k, v in local.projects_grouped : k => v[length(v) - 1]
  }
}
