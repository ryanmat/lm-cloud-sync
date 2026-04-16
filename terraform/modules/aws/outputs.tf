# Description: Output values for the AWS LM Cloud Sync Terraform module.
# Description: Exposes managed account IDs, counts, and LM group IDs.

output "managed_accounts" {
  description = "List of managed AWS account IDs"
  value       = keys(local.accounts)
}

output "account_count" {
  description = "Number of managed AWS accounts"
  value       = length(local.accounts)
}

output "group_ids" {
  description = "Map of account ID to LM device group ID"
  value = {
    for k, v in logicmonitor_device_group.aws_account : k => v.id
  }
}

output "external_id" {
  description = "LM external ID for AWS cross-account IAM role trust policies"
  value       = data.logicmonitor_aws_external_id.this.external_id
}
