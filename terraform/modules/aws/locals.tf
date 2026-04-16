# Description: Local values for the AWS LM Cloud Sync Terraform module.
# Description: Computes service config, merges account sources, and resolves the external ID.

locals {
  # Service monitoring config -- identical structure per service
  service_config = {
    for svc in var.services : svc => {
      useDefault                    = true
      selectAll                     = false
      monitoringRegions             = var.regions
      tags                          = []
      nameFilter                    = []
      deadOperation                 = var.dead_operation
      disableTerminatedHostAlerting = var.disable_terminated_alerting
    }
  }

  # Default monitoring settings
  default_config = {
    useDefault                    = true
    selectAll                     = false
    monitoringRegions             = var.regions
    tags                          = []
    nameFilter                    = []
    deadOperation                 = var.dead_operation
    disableTerminatedHostAlerting = var.disable_terminated_alerting
  }

  # Custom properties as list of {name, value} objects (LM API format)
  custom_props = [
    for k, v in var.custom_properties : { name = k, value = v }
  ]

  # Account sources: merge discovered + static + file
  accounts_from_file = var.accounts_file != "" ? yamldecode(file(var.accounts_file)).accounts : []
  static_list        = length(var.accounts) > 0 ? var.accounts : local.accounts_from_file

  discovered_list = var.auto_discover ? [
    for acct in data.aws_organizations_organization.org[0].accounts : {
      account_id   = acct.id
      display_name = acct.name
    }
    if acct.status == "ACTIVE"
    && !contains(var.exclude_account_ids, acct.id)
  ] : []

  # Merge: static entries override discovered
  merged_list = concat(local.discovered_list, local.static_list)

  accounts_grouped = {
    for a in local.merged_list : a.account_id => a...
  }

  # Final account map: keyed by account_id
  accounts = {
    for k, v in local.accounts_grouped : k => v[length(v) - 1]
  }
}
