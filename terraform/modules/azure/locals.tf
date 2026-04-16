# Description: Local values for the Azure LM Cloud Sync Terraform module.
# Description: Computes service config and subscription map for LM integration.

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

  # Subscription map for LM integration (keyed by subscription_id)
  subscription_map = {
    for sub_id in var.subscription_ids : sub_id => {
      subscription_id = sub_id
      display_name    = sub_id
    }
  }
}
