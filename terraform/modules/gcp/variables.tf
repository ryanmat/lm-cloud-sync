# LM Cloud Sync - GCP Module Variables

variable "lm_bearer_token" {
  description = "LogicMonitor Bearer Token"
  type        = string
  sensitive   = true
}

variable "lm_company" {
  description = "LogicMonitor company name (portal subdomain)"
  type        = string
}

variable "lm_parent_group_id" {
  description = "Parent group ID for GCP integrations"
  type        = number
  default     = 1
}

variable "gcp_service_account_key_path" {
  description = "Path to GCP service account key JSON file"
  type        = string
}

variable "projects" {
  description = "List of GCP projects to integrate (alternative to projects_file)"
  type = list(object({
    project_id   = string
    display_name = optional(string)
  }))
  default = []
}

variable "projects_file" {
  description = "Path to YAML file with project list (alternative to projects variable)"
  type        = string
  default     = ""
}

variable "python_command" {
  description = "Python command to use (e.g., 'python3', 'uv run python3')"
  type        = string
  default     = "python3"
}

variable "monitoring_config" {
  description = "Default monitoring configuration"
  type = object({
    netscan_frequency           = optional(string, "0 * * * *")
    dead_operation              = optional(string, "KEEP_7_DAYS")
    disable_terminated_alerting = optional(bool, true)
    regions                     = optional(list(string), ["us-central1", "us-east1"])
    services                    = optional(list(string), [
      "APPENGINE",
      "BIGQUERY",
      "BIGTABLE",
      "CLOUDFUNCTION",
      "CLOUDRUN",
      "CLOUDSQL",
      "CLOUDTASKS",
      "COMPOSER",
      "COMPUTEENGINE",
      "DATAFLOW",
      "DATAPROC",
      "FILESTORE",
      "FIRESTORE",
      "GKE",
      "INTERCONNECT",
      "LOADBALANCING",
      "PUBSUB",
      "REDIS",
      "SPANNER",
      "STORAGE",
      "VPN",
    ])
  })
  default = {}
}
