# LM Cloud Sync - GCP Module Outputs

output "managed_projects" {
  description = "List of managed GCP project IDs"
  value       = keys(local.projects)
}

output "project_count" {
  description = "Number of managed projects"
  value       = length(local.projects)
}
