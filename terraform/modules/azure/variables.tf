# Description: Input variables for the Azure LM Cloud Sync Terraform module.
# Description: Defines Azure SP settings and optional LM integration config.

# Azure AD settings
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

# LM integration settings (optional -- set enable_lm_integration = true to create LM device groups)
variable "enable_lm_integration" {
  description = "Create LogicMonitor device groups for each subscription. Requires lm_api_id, lm_api_key, lm_company."
  type        = bool
  default     = false
}

variable "lm_api_id" {
  description = "LogicMonitor API access ID (required when enable_lm_integration = true)"
  type        = string
  default     = ""
}

variable "lm_api_key" {
  description = "LogicMonitor API access key (required when enable_lm_integration = true)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "lm_company" {
  description = "LogicMonitor portal company name (required when enable_lm_integration = true)"
  type        = string
  default     = ""
}

variable "lm_parent_group_id" {
  description = "Parent group ID in LogicMonitor for Azure integrations"
  type        = number
  default     = 1
}

variable "regions" {
  description = "Azure regions to monitor"
  type        = list(string)
  default     = ["eastus", "westus2"]
}

variable "services" {
  description = "Azure services to enable monitoring for"
  type        = list(string)
  default = [
    "APIMANAGEMENT", "APPLICATIONGATEWAY", "APPSERVICE", "AUTOMATIONACCOUNT",
    "BATCHACCOUNT", "CDNPROFILE", "COGNITIVESERVICES", "CONTAINERINSTANCE",
    "CONTAINERREGISTRY", "COSMOSDB", "DATABRICKS", "DATAFACTORY",
    "DATALAKEANALYTICS", "DATALAKESTORE", "EVENTGRID", "EVENTHUB",
    "EXPRESSROUTE", "FIREWALL", "FRONTDOOR", "FUNCTIONS",
    "HDINSIGHT", "IOTHUB", "KEYVAULT", "KUSTO",
    "LOADBALANCER", "LOGICAPPS", "MARIADB", "MYSQL",
    "NOTIFICATIONHUB", "POSTGRESQL", "REDISCACHE", "SEARCHSERVICE",
    "SERVICEBUS", "SIGNALR", "SQLDATABASE", "SQLMANAGEDINSTANCE",
    "STORAGEACCOUNT", "STREAMANALYTICS", "SYNAPSE",
    "VIRTUALMACHINE", "VIRTUALMACHINESCALESET", "VPNGATEWAY",
  ]
}

variable "schedule" {
  description = "Netscan cron schedule"
  type        = string
  default     = "0 * * * *"
}

variable "dead_operation" {
  description = "Action for terminated instances"
  type        = string
  default     = "KEEP_7_DAYS"
}

variable "disable_terminated_alerting" {
  description = "Disable alerting on terminated hosts"
  type        = bool
  default     = true
}

variable "group_name_template" {
  description = "Template for LM group names. Supports {subscription_id} and {display_name} placeholders."
  type        = string
  default     = "Azure - {subscription_id}"
}

variable "custom_properties" {
  description = "Custom properties to set on each LM device group"
  type        = map(string)
  default     = {}
}
