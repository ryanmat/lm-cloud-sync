# Outputs for AWS LM integration module

output "managed_accounts" {
  description = "List of AWS account IDs managed by this module"
  value       = keys(local.accounts)
}

output "account_count" {
  description = "Number of AWS accounts managed"
  value       = length(local.accounts)
}
