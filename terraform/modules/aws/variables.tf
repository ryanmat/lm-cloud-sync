# Variables for AWS LM integration module

variable "lm_company" {
  description = "LogicMonitor company/portal name"
  type        = string
}

variable "lm_bearer_token" {
  description = "LogicMonitor Bearer Token for API authentication"
  type        = string
  sensitive   = true
}

variable "lm_parent_group_id" {
  description = "Parent group ID in LogicMonitor for AWS integrations"
  type        = number
  default     = 1
}

variable "aws_role_name" {
  description = "Name of the IAM role to assume in each AWS account"
  type        = string
  default     = "LogicMonitorRole"
}

variable "accounts" {
  description = "List of AWS accounts to integrate with LogicMonitor"
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
  description = "Use AWS Organizations to auto-discover accounts"
  type        = bool
  default     = false
}

variable "python_command" {
  description = "Python command to use for running scripts"
  type        = string
  default     = "python3"
}
