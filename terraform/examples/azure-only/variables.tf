# Variables for Azure-only example

variable "subscription_ids" {
  description = "List of Azure subscription IDs to grant access to"
  type        = list(string)
}

variable "application_name" {
  description = "Name for the Azure AD application"
  type        = string
  default     = "LogicMonitor Cloud Integration"
}

variable "enable_monitoring_reader" {
  description = "Assign Monitoring Reader role for enhanced metrics"
  type        = bool
  default     = true
}

variable "enable_log_analytics" {
  description = "Assign Log Analytics Reader role"
  type        = bool
  default     = false
}
