# Description: Variables for the AWS-only Terraform example.
# Description: LM API credentials and AWS role configuration.

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
  description = "LogicMonitor company name"
  type        = string
}

variable "lm_parent_group_id" {
  description = "Parent group ID for integrations"
  type        = number
  default     = 1
}

variable "aws_role_name" {
  description = "IAM role name to assume in each AWS account"
  type        = string
  default     = "LogicMonitorRole"
}
