# Description: Input variables for the AWS LM Cloud Sync Terraform module.
# Description: Defines LM credentials, AWS settings, and optional Organizations auto-discovery.

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
  description = "Parent group ID in LogicMonitor for AWS integrations"
  type        = number
  default     = 1
}

# AWS settings
variable "aws_role_name" {
  description = "IAM role name to assume in each AWS account"
  type        = string
  default     = "LogicMonitorRole"
}

# Account sources (at least one of: accounts, accounts_file, or auto_discover)
variable "accounts" {
  description = "Static list of AWS accounts to integrate"
  type = list(object({
    account_id   = string
    display_name = optional(string)
  }))
  default = []
}

variable "accounts_file" {
  description = "Path to YAML file containing AWS accounts list"
  type        = string
  default     = ""
}

variable "auto_discover" {
  description = "Use AWS Organizations API to discover accounts. Requires organizations:ListAccounts permission."
  type        = bool
  default     = false
}

variable "exclude_account_ids" {
  description = "Account IDs to exclude from auto-discovery"
  type        = list(string)
  default     = []
}

# Monitoring configuration
variable "regions" {
  description = "AWS regions to monitor"
  type        = list(string)
  default     = ["us-east-1", "us-west-2"]
}

variable "services" {
  description = "AWS services to enable monitoring for"
  type        = list(string)
  default     = ["EC2", "RDS", "S3"]
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
  description = "Template for LM group names. Supports {account_id} and {display_name} placeholders."
  type        = string
  default     = "AWS - {account_id}"
}

variable "custom_properties" {
  description = "Custom properties to set on each LM device group"
  type        = map(string)
  default     = {}
}
