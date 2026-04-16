# Description: Input variables for the GCP LM Cloud Sync Terraform module.
# Description: Defines LM credentials, GCP settings, and optional auto-discovery config.

# LogicMonitor credentials (LMv1 auth)
variable "lm_api_id" {
  description = "LogicMonitor API access ID"
  type        = string
}

variable "lm_api_key" {
  description = "LogicMonitor API access key"
  type        = string
  sensitive   = true
}

variable "lm_company" {
  description = "LogicMonitor portal company name (subdomain)"
  type        = string
}

variable "lm_parent_group_id" {
  description = "Parent group ID in LogicMonitor for GCP integrations"
  type        = number
  default     = 1
}

# GCP settings
variable "gcp_service_account_key_path" {
  description = "Path to GCP service account JSON key file"
  type        = string
}

# Project sources (at least one of: projects, projects_file, or gcp_org_id)
variable "projects" {
  description = "Static list of GCP projects to integrate"
  type = list(object({
    project_id   = string
    display_name = optional(string)
  }))
  default = []
}

variable "projects_file" {
  description = "Path to YAML file containing GCP projects list"
  type        = string
  default     = ""
}

variable "gcp_org_id" {
  description = "GCP organization numeric ID for auto-discovery. When set, discovers all ACTIVE projects."
  type        = string
  default     = ""
}

variable "exclude_project_ids" {
  description = "Project IDs to exclude from auto-discovery"
  type        = list(string)
  default     = []
}

# Monitoring configuration
variable "regions" {
  description = "GCP regions to monitor"
  type        = list(string)
  default     = ["us-central1", "us-east1"]
}

variable "services" {
  description = "GCP services to enable monitoring for"
  type        = list(string)
  default = [
    "APPENGINE", "BIGQUERY", "BIGTABLE", "CLOUDFUNCTION", "CLOUDRUN",
    "CLOUDSQL", "CLOUDTASKS", "COMPOSER", "COMPUTEENGINE", "DATAFLOW",
    "DATAPROC", "FILESTORE", "FIRESTORE", "GKE", "INTERCONNECT",
    "LOADBALANCING", "PUBSUB", "REDIS", "SPANNER", "STORAGE", "VPN",
  ]
}

variable "schedule" {
  description = "Netscan cron schedule"
  type        = string
  default     = "0 * * * *"
}

variable "dead_operation" {
  description = "Action for terminated instances (MANUALLY, KEEP_7_DAYS, KEEP_14_DAYS, KEEP_30_DAYS, IMMEDIATELY)"
  type        = string
  default     = "KEEP_7_DAYS"
}

variable "disable_terminated_alerting" {
  description = "Disable alerting on terminated hosts"
  type        = bool
  default     = true
}

variable "group_name_template" {
  description = "Template for LM group names. Supports {project_id} and {display_name} placeholders."
  type        = string
  default     = "GCP - {project_id}"
}

variable "custom_properties" {
  description = "Custom properties to set on each LM device group"
  type        = map(string)
  default     = {}
}
