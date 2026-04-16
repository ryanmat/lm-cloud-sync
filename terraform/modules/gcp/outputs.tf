# Description: Output values for the GCP LM Cloud Sync Terraform module.
# Description: Exposes managed project IDs, counts, and LM group IDs.

output "managed_projects" {
  description = "List of managed GCP project IDs"
  value       = keys(local.projects)
}

output "project_count" {
  description = "Number of managed GCP projects"
  value       = length(local.projects)
}

output "group_ids" {
  description = "Map of project ID to LM device group ID"
  value = {
    for k, v in logicmonitor_device_group.gcp_project : k => v.id
  }
}
