# LM Cloud Sync - Terraform Modules

Terraform modules for managing LogicMonitor cloud integrations.

**Package Version:** v3.0.0 (`pip install lm-cloud-sync`)
**Terraform Modules:** v2.x (use bearer token auth via Python scripts)

## Available Modules

| Module | Description | Status | Since |
|--------|-------------|--------|-------|
| [gcp](./modules/gcp) | GCP project integrations | Available | v2.0.0 |
| [azure](./modules/azure) | Azure Service Principal setup | Available | v2.0.5 |
| [aws](./modules/aws) | AWS account integrations | Available | v2.1.0 |

## GCP Module

Creates LogicMonitor device groups for GCP projects.

### Usage

```hcl
module "gcp_integrations" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/gcp"

  lm_company                   = "your-company"
  lm_bearer_token              = var.lm_bearer_token
  gcp_service_account_key_path = "/path/to/service-account.json"

  # Option 1: Define projects inline
  projects = [
    {
      project_id   = "my-project-1"
      display_name = "My Project 1"
    },
    {
      project_id   = "my-project-2"
      display_name = "My Project 2"
    },
  ]

  # Option 2: Load from YAML file
  # projects_file = "projects.yaml"
}
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `lm_company` | LogicMonitor portal name | string | - | Yes |
| `lm_bearer_token` | LogicMonitor Bearer token | string | - | Yes |
| `gcp_service_account_key_path` | Path to GCP SA key JSON | string | - | Yes |
| `lm_parent_group_id` | Parent group ID | number | 1 | No |
| `projects` | List of projects to integrate | list | [] | No* |
| `projects_file` | Path to YAML file with projects | string | "" | No* |
| `python_command` | Python command to use | string | "python3" | No |

*Either `projects` or `projects_file` must be provided.

### Projects YAML Format

```yaml
projects:
  - project_id: my-gcp-project-1
    display_name: "Production Project"
  - project_id: my-gcp-project-2
    display_name: "Development Project"
```

### Outputs

| Name | Description |
|------|-------------|
| `managed_projects` | List of managed GCP project IDs |
| `project_count` | Number of managed projects |

## AWS Module

Creates LogicMonitor device groups for AWS accounts.

### Prerequisites

Before using this module, you must:

1. Create an IAM role in each AWS account with a trust policy allowing LogicMonitor to assume the role
2. The trust policy must include the external ID from LogicMonitor

### Usage

```hcl
module "aws_integrations" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/aws"

  lm_company      = "your-company"
  lm_bearer_token = var.lm_bearer_token
  aws_role_name   = "LogicMonitorRole"

  # Option 1: Define accounts inline
  accounts = [
    {
      account_id   = "123456789012"
      display_name = "Production Account"
    },
    {
      account_id   = "234567890123"
      display_name = "Development Account"
    },
  ]

  # Option 2: Load from YAML file
  # accounts_file = "accounts.yaml"
}
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `lm_company` | LogicMonitor portal name | string | - | Yes |
| `lm_bearer_token` | LogicMonitor Bearer token | string | - | Yes |
| `aws_role_name` | IAM role name to assume | string | "LogicMonitorRole" | No |
| `lm_parent_group_id` | Parent group ID | number | 1 | No |
| `accounts` | List of AWS accounts | list | [] | No* |
| `accounts_file` | Path to YAML file with accounts | string | "" | No* |
| `auto_discover` | Use Organizations API | bool | false | No |
| `python_command` | Python command to use | string | "python3" | No |

*Either `accounts` or `accounts_file` must be provided (unless using auto_discover).

### Accounts YAML Format

```yaml
accounts:
  - account_id: "123456789012"
    display_name: "Production Account"
  - account_id: "234567890123"
    display_name: "Development Account"
```

### Outputs

| Name | Description |
|------|-------------|
| `managed_accounts` | List of managed AWS account IDs |
| `account_count` | Number of managed accounts |

### IAM Role Setup

Each AWS account needs an IAM role that LogicMonitor can assume:

1. Get the external ID from LogicMonitor: `lm-cloud-sync aws discover --auto-discover` (requires setup first)
2. Create an IAM role with the following trust policy:

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

3. Attach a policy with read-only permissions for the AWS services you want to monitor.

## Azure Module

Creates Azure AD Service Principal and role assignments for LogicMonitor integration.

**Note:** This module creates the Azure prerequisites (Service Principal with credentials). Use `lm-cloud-sync azure sync` CLI to create LogicMonitor integrations.

### Usage

```hcl
module "logicmonitor_azure" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/azure"

  subscription_ids = [
    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  ]

  # Optional settings
  application_name         = "LogicMonitor Cloud Integration"
  enable_monitoring_reader = true
  enable_log_analytics     = false
}

# After apply, use credentials with lm-cloud-sync CLI
output "azure_credentials" {
  value     = module.logicmonitor_azure.lm_cloud_sync_env
  sensitive = true
}
```

### Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `subscription_ids` | List of Azure subscription IDs | list(string) | - | Yes |
| `application_name` | Name for Azure AD application | string | "LogicMonitor Cloud Integration" | No |
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

### Using with lm-cloud-sync CLI

After Terraform apply:

```bash
# Export credentials from Terraform output
export AZURE_TENANT_ID="$(terraform output -raw tenant_id)"
export AZURE_CLIENT_ID="$(terraform output -raw client_id)"
export AZURE_CLIENT_SECRET="$(terraform output -raw client_secret)"

# Set LogicMonitor credentials
export LM_COMPANY="your-company"
export LM_BEARER_TOKEN="your-token"

# Discover and sync
lm-cloud-sync azure discover --auto-discover
lm-cloud-sync azure sync --auto-discover --dry-run
lm-cloud-sync azure sync --auto-discover --yes
```

## Prerequisites

1. **lm-cloud-sync installed**:
   ```bash
   pip install lm-cloud-sync
   # or
   uv tool install lm-cloud-sync
   ```

2. **Cloud Provider Credentials**:
   - GCP: Service Account with Viewer role
   - Azure: Service Principal with Reader role (or use the Azure module to create one)
   - AWS: IAM role with cross-account trust policy

3. **LogicMonitor API credentials** (Bearer token or LMv1)

## Examples

See the [examples](./examples) directory:

- [gcp-only](./examples/gcp-only) - GCP project integration
- [azure-only](./examples/azure-only) - Azure Service Principal setup

## How It Works

### GCP Module

Uses Terraform's `null_resource` with `local-exec` provisioners to:

1. **On Apply**: Runs `create_integration.py` to create LM device groups
2. **On Destroy**: Runs `delete_integration.py` to remove LM device groups

This approach allows Terraform to manage the lifecycle of LogicMonitor integrations while leveraging the lm-cloud-sync library for API communication.

### Azure Module

Uses native Terraform Azure providers (`azuread` and `azurerm`) to:

1. Create Azure AD Application and Service Principal
2. Generate client secret for authentication
3. Assign Reader role (and optional Monitoring Reader, Log Analytics Reader) to subscriptions

After Terraform creates the credentials, use `lm-cloud-sync azure sync` CLI to create the LogicMonitor integrations. This separation allows:

- Terraform to manage Azure IAM resources (proper state management)
- CLI to handle LogicMonitor API calls with auto-discovery capabilities
