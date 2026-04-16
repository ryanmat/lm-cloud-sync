# Description: Variables for the Azure-only Terraform example.
# Description: Azure subscription IDs, SP settings, and optional LM credentials.

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

# LM credentials (needed for Option 2: full integration)
variable "lm_api_id" {
  description = "LogicMonitor API access ID"
  type        = string
  default     = ""
}

variable "lm_api_key" {
  description = "LogicMonitor API access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "lm_company" {
  description = "LogicMonitor company name"
  type        = string
  default     = ""
}
