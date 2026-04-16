# LM Cloud Sync - Terraform Modules

Terraform modules for managing LogicMonitor cloud integrations.

**Provider:** [`ryanmat/logicmonitor`](https://github.com/ryanmat/rm-logicmonitor-terraform-provider) (LMv1 auth)
**CLI Package:** `pip install lm-cloud-sync` (for Azure sync and operational commands)

## Available Modules

| Module | Description | Status |
|--------|-------------|--------|
| [gcp](./modules/gcp) | GCP project integrations (auto-discovery or static list) | Available |
| [aws](./modules/aws) | AWS account integrations (Organizations discovery or static list) | Available |
| [azure](./modules/azure) | Azure Service Principal + role assignments | Available |

## Two Paths to LM Cloud Integration

**Terraform (GCP + AWS):** Manages the full lifecycle of LM device groups. Discovery via native cloud data sources, CRUD via the `logicmonitor_device_group` resource. Real state management, plan visibility, drift detection.

**CLI (all providers, especially Azure):** Stateless sync with auto-discovery. Best for Azure because the LM API masks the `secretKey` in GET responses, which causes update-on-every-apply in Terraform. Use `lm-cloud-sync azure sync --yes` instead.

## GCP Module

Creates LogicMonitor device groups for GCP projects.

### Usage

```hcl
provider "logicmonitor" {
  api_id  = var.lm_api_id
  api_key = var.lm_api_key
  company = var.lm_company
}

# Option 1: Static project list
module "gcp_integrations" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/gcp"

  lm_api_id                    = var.lm_api_id
  lm_api_key                   = var.lm_api_key
  lm_company                   = var.lm_company
  gcp_service_account_key_path = "/path/to/service-account.json"

  projects = [
    { project_id = "my-project-1", display_name = "Production" },
    { project_id = "my-project-2", display_name = "Development" },
  ]
}

# Option 2: Auto-discover all projects in an organization
module "gcp_auto" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/gcp"

  lm_api_id                    = var.lm_api_id
  lm_api_key                   = var.lm_api_key
  lm_company                   = var.lm_company
  gcp_service_account_key_path = "/path/to/service-account.json"

  gcp_org_id          = "123456789012"
  exclude_project_ids = ["sandbox-project"]
}
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `lm_api_id` | LM API access ID | string | - | Yes |
| `lm_api_key` | LM API access key | string | - | Yes |
| `lm_company` | LM portal company name | string | - | Yes |
| `gcp_service_account_key_path` | Path to GCP SA key JSON | string | - | Yes |
| `lm_parent_group_id` | Parent group ID | number | 1 | No |
| `projects` | Static list of projects | list | [] | No |
| `projects_file` | YAML file with projects | string | "" | No |
| `gcp_org_id` | GCP org ID for auto-discovery | string | "" | No |
| `exclude_project_ids` | Project IDs to exclude | list | [] | No |
| `regions` | GCP regions to monitor | list | ["us-central1", "us-east1"] | No |
| `services` | GCP services to monitor | list | 21 services | No |
| `schedule` | Netscan cron schedule | string | "0 * * * *" | No |
| `group_name_template` | Group name template | string | "GCP - {project_id}" | No |
| `custom_properties` | Custom properties | map | {} | No |

### Outputs

| Name | Description |
|------|-------------|
| `managed_projects` | List of managed GCP project IDs |
| `project_count` | Number of managed projects |
| `group_ids` | Map of project ID to LM device group ID |

## AWS Module

Creates LogicMonitor device groups for AWS accounts.

### Prerequisites

Each AWS account needs an IAM role that LogicMonitor can assume. The module outputs the `external_id` needed for the trust policy.

### Usage

```hcl
provider "logicmonitor" {
  api_id  = var.lm_api_id
  api_key = var.lm_api_key
  company = var.lm_company
}

# Option 1: Static account list
module "aws_integrations" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/aws"

  lm_api_id     = var.lm_api_id
  lm_api_key    = var.lm_api_key
  lm_company    = var.lm_company
  aws_role_name = "LogicMonitorRole"

  accounts = [
    { account_id = "123456789012", display_name = "Production" },
    { account_id = "234567890123", display_name = "Development" },
  ]
}

# Option 2: Auto-discover via AWS Organizations
module "aws_auto" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/aws"

  lm_api_id     = var.lm_api_id
  lm_api_key    = var.lm_api_key
  lm_company    = var.lm_company
  aws_role_name = "LogicMonitorRole"

  auto_discover       = true
  exclude_account_ids = ["999999999999"]  # management account
}
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `lm_api_id` | LM API access ID | string | - | Yes |
| `lm_api_key` | LM API access key | string | - | Yes |
| `lm_company` | LM portal company name | string | - | Yes |
| `lm_parent_group_id` | Parent group ID | number | 1 | No |
| `aws_role_name` | IAM role name to assume | string | "LogicMonitorRole" | No |
| `accounts` | Static list of accounts | list | [] | No |
| `accounts_file` | YAML file with accounts | string | "" | No |
| `auto_discover` | Use Organizations API | bool | false | No |
| `exclude_account_ids` | Account IDs to exclude | list | [] | No |
| `regions` | AWS regions to monitor | list | ["us-east-1", "us-west-2"] | No |
| `services` | AWS services to monitor | list | ["EC2", "RDS", "S3"] | No |
| `schedule` | Netscan cron schedule | string | "0 * * * *" | No |
| `group_name_template` | Group name template | string | "AWS - {account_id}" | No |
| `custom_properties` | Custom properties | map | {} | No |

### Outputs

| Name | Description |
|------|-------------|
| `managed_accounts` | List of managed AWS account IDs |
| `account_count` | Number of managed accounts |
| `group_ids` | Map of account ID to LM device group ID |
| `external_id` | LM external ID for IAM trust policies |

### IAM Role Trust Policy

Use the `external_id` output in each account's IAM role trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::282028653949:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "YOUR_EXTERNAL_ID"
        }
      }
    }
  ]
}
```

## Azure Module

Creates Azure AD Service Principal and role assignments for LogicMonitor integration.

**Note:** This module creates the Azure prerequisites only. Use `lm-cloud-sync azure sync` CLI to create LogicMonitor device groups. This separation exists because the LM API masks Azure credentials in GET responses, making Terraform state management unreliable for Azure cloud groups.

### Usage

```hcl
module "logicmonitor_azure" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/azure"

  subscription_ids = [
    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  ]
}

# After apply, use credentials with the CLI
# export AZURE_TENANT_ID="$(terraform output -raw tenant_id)"
# export AZURE_CLIENT_ID="$(terraform output -raw client_id)"
# export AZURE_CLIENT_SECRET="$(terraform output -raw client_secret)"
# lm-cloud-sync azure sync --yes
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `subscription_ids` | Azure subscription IDs | list(string) | - | Yes |
| `application_name` | Azure AD application name | string | "LogicMonitor Cloud Integration" | No |
| `secret_expiration_date` | Secret expiration (ISO 8601) | string | null (2 years) | No |
| `enable_monitoring_reader` | Assign Monitoring Reader role | bool | true | No |
| `enable_log_analytics` | Assign Log Analytics Reader role | bool | false | No |

### Outputs

| Name | Description |
|------|-------------|
| `tenant_id` | Azure AD tenant ID |
| `client_id` | Application (client) ID |
| `client_secret` | Client secret (sensitive) |
| `lm_cloud_sync_env` | Environment variables for CLI |
| `setup_instructions` | Usage instructions |

## Prerequisites

1. **LogicMonitor Terraform provider** (`ryanmat/logicmonitor`) installed
2. **LM API credentials** (LMv1 access ID + access key)
3. **Cloud provider credentials** as needed:
   - GCP: Service Account with `resourcemanager.projects.list` at org level (for auto-discovery) or Viewer on target projects
   - AWS: `organizations:DescribeOrganization` + `organizations:ListAccounts` on management account (for auto-discovery)
   - Azure: Credentials for `azuread` and `azurerm` providers

## Examples

See the [examples](./examples) directory:

- [gcp-only](./examples/gcp-only) - GCP project integration
- [aws-only](./examples/aws-only) - AWS account integration
- [azure-only](./examples/azure-only) - Azure Service Principal setup

## Migration from v2.x Modules

The v3.x modules use `ryanmat/logicmonitor` provider instead of `null_resource` + Python scripts. Key changes:

1. **Auth**: Replace `lm_bearer_token` with `lm_api_id` + `lm_api_key`
2. **Provider**: Add `ryanmat/logicmonitor` to `required_providers`
3. **Python**: No longer required on the Terraform runner
4. **State**: Existing `null_resource` state is not compatible. Re-import groups with `terraform import`
5. **Auto-discovery**: Uses native cloud data sources instead of the CLI
