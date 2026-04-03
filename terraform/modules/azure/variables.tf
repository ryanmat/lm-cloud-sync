# Variables for Azure LogicMonitor Service Principal module

variable "application_name" {
  description = "Name for the Azure AD application"
  type        = string
  default     = "LogicMonitor Cloud Integration"
}

variable "subscription_ids" {
  description = "List of Azure subscription IDs to grant access to"
  type        = list(string)

  validation {
    condition     = length(var.subscription_ids) > 0
    error_message = "At least one subscription ID must be provided."
  }
}

variable "secret_expiration_date" {
  description = "Expiration date for the service principal secret (ISO 8601 format)"
  type        = string
  default     = null # Will use Azure default (2 years)

  validation {
    condition     = var.secret_expiration_date == null || can(regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$", var.secret_expiration_date))
    error_message = "Secret expiration date must be in ISO 8601 format (e.g., 2025-12-31T23:59:59Z)."
  }
}

variable "enable_monitoring_reader" {
  description = "Assign Monitoring Reader role for enhanced Azure Monitor access"
  type        = bool
  default     = true
}

variable "enable_log_analytics" {
  description = "Assign Log Analytics Reader role for log access"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags for the Azure AD application"
  type        = list(string)
  default     = []
}
