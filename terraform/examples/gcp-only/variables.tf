# Variables for GCP-only example

variable "lm_company" {
  description = "LogicMonitor company name"
  type        = string
}

variable "lm_bearer_token" {
  description = "LogicMonitor Bearer Token"
  type        = string
  sensitive   = true
}

variable "lm_parent_group_id" {
  description = "Parent group ID for integrations"
  type        = number
  default     = 1
}

variable "gcp_service_account_key_path" {
  description = "Path to GCP service account key JSON"
  type        = string
}
