# LM Cloud Sync - CLI Guide

Command-line tool for discovering cloud resources and syncing them to LogicMonitor.

**Current Version:** v3.0.0 - Full Multi-Cloud Support

## Overview

| Command | Description |
|---------|-------------|
| `gcp discover` | List all GCP projects accessible by your service account |
| `gcp status` | Compare GCP projects with existing LogicMonitor integrations |
| `gcp sync` | Create LogicMonitor integrations for GCP projects |
| `gcp delete` | Delete a specific LogicMonitor GCP integration |
| `gcp resync` | Trigger LM sync engine on existing GCP integrations |
| `aws discover` | List all AWS accounts in your organization |
| `aws status` | Compare AWS accounts with existing LogicMonitor integrations |
| `aws sync` | Create LogicMonitor integrations for AWS accounts |
| `aws delete` | Delete a specific LogicMonitor AWS integration |
| `aws resync` | Trigger LM sync engine on existing AWS integrations |
| `azure discover` | List all Azure subscriptions accessible to your credentials |
| `azure status` | Compare Azure subscriptions with existing LogicMonitor integrations |
| `azure sync` | Create LogicMonitor integrations for Azure subscriptions |
| `azure delete` | Delete a specific LogicMonitor Azure integration |
| `azure resync` | Trigger LM sync engine on existing Azure integrations |
| `config init` | Create a configuration file template |
| `config validate` | Validate a configuration file |

## Prerequisites

- Python 3.11+
- uv package manager (recommended) or pip
- Cloud provider credentials (GCP Service Account, AWS IAM Role, Azure Service Principal)
- LogicMonitor API Bearer token or LMv1 credentials

## Installation

```bash
# Using uv (recommended)
uv tool install lm-cloud-sync

# Or using pip
pip install lm-cloud-sync
```

## Configuration

### Environment Variables

```bash
# LogicMonitor API Configuration
export LM_COMPANY=your-company-name

# Option 1: Bearer token auth
export LM_BEARER_TOKEN=lmb_xxxxx

# Option 2: LMv1 auth (access ID + access key)
export LM_ACCESS_ID=your-access-id
export LM_ACCESS_KEY=your-access-key

# Auth method is auto-detected from which credentials are set.
# If both are present, Bearer token takes precedence.

# GCP Service Account Key Path
export GCP_SA_KEY_PATH=/path/to/service-account.json

# AWS IAM Credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Azure Service Principal
export AZURE_TENANT_ID=your-tenant-id
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
```

### Configuration File (Optional)

Create a config file with `lm-cloud-sync config init`:

```yaml
logicmonitor:
  company: your-company
  parent_group_id: 1

gcp:
  enabled: true
  service_account_key_path: /path/to/key.json
  filters:
    exclude_patterns: ["sys-*", "test-*"]

aws:
  enabled: true
  role_name: LogicMonitorRole
  filters:
    exclude_patterns: ["sandbox-*"]

azure:
  enabled: true
  filters:
    exclude_patterns: ["sandbox-*"]

sync:
  dry_run: false
  delete_orphans: false
```

## Command Reference

### GCP Commands

#### gcp discover

Lists all GCP projects accessible by your service account.

```bash
lm-cloud-sync gcp discover

# With auto-discovery (org-level)
lm-cloud-sync gcp discover --auto-discover

# Output as JSON
lm-cloud-sync gcp discover --output json
```

Example Output:

```
Discovering GCP projects...

Found 3 GCP projects:
+--------------------------+--------------------------+----------------+
| Project ID               | Display Name             | Project Number |
+--------------------------+--------------------------+----------------+
| project-alpha            | Project Alpha            | 123456789      |
| project-beta             | Project Beta             | 234567890      |
| project-gamma            | Project Gamma            | 345678901      |
+--------------------------+--------------------------+----------------+
```

#### gcp status

Compares GCP projects with existing LogicMonitor integrations.

```bash
lm-cloud-sync gcp status

# Show orphaned integrations (exist in LM but not in GCP)
lm-cloud-sync gcp status --show-orphans
```

Example Output:

```
Checking sync status...

GCP Projects: 3
LogicMonitor Integrations: 1

New projects (not in LogicMonitor):
  - project-alpha
  - project-beta

Already integrated:
  - project-gamma -> Group ID 456
```

#### gcp sync

Creates LogicMonitor integrations for GCP projects.

```bash
# Preview changes (dry run)
lm-cloud-sync gcp sync --dry-run

# Execute sync (requires confirmation)
lm-cloud-sync gcp sync

# Execute sync (skip confirmation)
lm-cloud-sync gcp sync --yes

# Sync to a specific LogicMonitor parent group
lm-cloud-sync gcp sync --parent-group-id 123 --yes

# Sync and delete orphaned integrations
lm-cloud-sync gcp sync --delete-orphans --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without making them |
| `--yes` | Skip confirmation prompt |
| `--parent-group-id`, `-p` | LogicMonitor parent group ID for new integrations |
| `--delete-orphans` | Remove integrations for projects no longer in GCP |
| `--auto-discover` | Use org-level discovery |

Example Output:

```
Syncing GCP projects to LogicMonitor...

Creating integration for project-alpha...
  Created: GCP - project-alpha (Group ID: 789)

Creating integration for project-beta...
  Created: GCP - project-beta (Group ID: 790)

Sync complete:
  Created: 2
  Skipped: 1 (already exists)
  Failed: 0
```

#### gcp delete

Delete a specific LogicMonitor GCP integration.

```bash
# Delete by project ID
lm-cloud-sync gcp delete --project-id my-project

# Skip confirmation
lm-cloud-sync gcp delete --project-id my-project --yes
```

#### gcp resync

Trigger the LM sync engine on existing GCP cloud root groups. Performs a full PUT to
trigger credential validation, region re-evaluation, and service re-discovery.

```bash
# Preview resync (dry run)
lm-cloud-sync gcp resync --all --dry-run

# Resync a specific group
lm-cloud-sync gcp resync --group-id 2584

# Resync all GCP groups
lm-cloud-sync gcp resync --all --yes

# Resync with modified regions
lm-cloud-sync gcp resync --all --extra-json '{"default": {"monitoringRegions": ["us-central1"]}}' --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--group-id` | Specific LM group ID to resync |
| `--all` | Resync all GCP cloud root groups |
| `--extra-json` | JSON string to merge into the extra field (modify regions, services, etc.) |
| `--dry-run` | Preview changes without applying |
| `--yes` | Skip confirmation prompt |

---

### AWS Commands

`--auto-discover` defaults to true for AWS. The Organizations API is used to discover accounts.

#### aws discover

Lists all AWS accounts in your organization.

```bash
lm-cloud-sync aws discover

# Output as JSON
lm-cloud-sync aws discover --output json
```

#### aws status

Compares AWS accounts with existing LogicMonitor integrations.

```bash
lm-cloud-sync aws status

# Show orphaned integrations
lm-cloud-sync aws status --show-orphans
```

#### aws sync

Creates LogicMonitor integrations for AWS accounts.

Prerequisites:
1. AWS credentials with `organizations:ListAccounts` permission
2. IAM role (`LogicMonitorRole`) created in each target account with LM trust policy
3. LogicMonitor API credentials

```bash
# Preview changes (dry run)
lm-cloud-sync aws sync --dry-run

# Execute sync (skip confirmation)
lm-cloud-sync aws sync --yes

# Sync to a specific parent group
lm-cloud-sync aws sync --parent-group-id 789 --yes

# Sync and delete orphaned integrations
lm-cloud-sync aws sync --delete-orphans --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without making them |
| `--yes` | Skip confirmation prompt |
| `--parent-group-id`, `-p` | LogicMonitor parent group ID for new integrations |
| `--delete-orphans` | Remove integrations for accounts no longer in the organization |
| `--auto-discover` | Use Organizations API (defaults to true) |

#### aws delete

Delete a specific LogicMonitor AWS integration.

```bash
# Delete by account ID
lm-cloud-sync aws delete --account-id 123456789012

# Skip confirmation
lm-cloud-sync aws delete --account-id 123456789012 --yes
```

#### aws resync

Trigger the LM sync engine on existing AWS cloud root groups. Performs a full PUT to
trigger credential validation, region re-evaluation, and service re-discovery.

```bash
# Preview resync (dry run)
lm-cloud-sync aws resync --all --dry-run

# Resync a specific group
lm-cloud-sync aws resync --group-id 1870

# Resync all AWS groups
lm-cloud-sync aws resync --all --yes

# Resync with modified regions
lm-cloud-sync aws resync --all --extra-json '{"default": {"monitoringRegions": ["us-east-1"]}}' --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--group-id` | Specific LM group ID to resync |
| `--all` | Resync all AWS cloud root groups |
| `--extra-json` | JSON string to merge into the extra field (modify regions, services, etc.) |
| `--dry-run` | Preview changes without applying |
| `--yes` | Skip confirmation prompt |

---

### Azure Commands

`--auto-discover` defaults to true for Azure. The Subscription Management API is used
to discover subscriptions.

#### azure discover

Lists all Azure subscriptions accessible to your Service Principal.

```bash
lm-cloud-sync azure discover

# Output as JSON
lm-cloud-sync azure discover --output json
```

#### azure status

Compares Azure subscriptions with existing LogicMonitor integrations.

```bash
lm-cloud-sync azure status

# Show orphaned integrations
lm-cloud-sync azure status --show-orphans
```

#### azure sync

Creates LogicMonitor integrations for Azure subscriptions.

Prerequisites:
1. Azure Service Principal with Reader role on target subscriptions
2. LogicMonitor API credentials

```bash
# Preview changes (dry run)
lm-cloud-sync azure sync --dry-run

# Execute sync (skip confirmation)
lm-cloud-sync azure sync --yes

# Sync to a specific parent group
lm-cloud-sync azure sync --parent-group-id 456 --yes

# Sync and delete orphaned integrations
lm-cloud-sync azure sync --delete-orphans --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without making them |
| `--yes` | Skip confirmation prompt |
| `--parent-group-id`, `-p` | LogicMonitor parent group ID for new integrations |
| `--delete-orphans` | Remove integrations for subscriptions no longer in Azure |
| `--auto-discover` | Use Subscription Management API (defaults to true) |

#### azure delete

Delete a specific LogicMonitor Azure integration.

```bash
# Delete by subscription ID
lm-cloud-sync azure delete --subscription-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Skip confirmation
lm-cloud-sync azure delete --subscription-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --yes
```

#### azure resync

Trigger the LM sync engine on existing Azure cloud root groups. Performs a full PUT to
trigger credential validation, region re-evaluation, and service re-discovery.

Azure `secretKey` is masked in GET responses. Use `--client-secret` to provide
the real value when resyncing.

```bash
# Preview resync (dry run)
lm-cloud-sync azure resync --all --dry-run

# Resync a specific group with secret override
lm-cloud-sync azure resync --group-id 2100 --client-secret <secret>

# Resync all Azure groups with secret
lm-cloud-sync azure resync --all --client-secret <secret> --yes

# Resync with modified regions
lm-cloud-sync azure resync --all --client-secret <secret> --extra-json '{"default": {"monitoringRegions": ["eastus"]}}' --yes
```

Options:

| Flag | Description |
|------|-------------|
| `--group-id` | Specific LM group ID to resync |
| `--all` | Resync all Azure cloud root groups |
| `--client-secret` | Azure client secret to override masked credential |
| `--extra-json` | JSON string to merge into the extra field (modify regions, services, etc.) |
| `--dry-run` | Preview changes without applying |
| `--yes` | Skip confirmation prompt |

---

### Config Commands

#### config init

Create a configuration file template.

```bash
# Create config.yaml in current directory
lm-cloud-sync config init

# Specify output path
lm-cloud-sync config init --output /path/to/config.yaml
```

#### config validate

Validate a configuration file.

```bash
# Validate default config.yaml
lm-cloud-sync config validate

# Validate a specific file
lm-cloud-sync config validate --config /path/to/config.yaml
```

## Scheduling with Cron

Run the sync on a schedule using cron:

```bash
# Edit crontab
crontab -e

# Add entry to sync every hour (GCP example)
0 * * * * LM_COMPANY=myco LM_BEARER_TOKEN=xxx GCP_SA_KEY_PATH=/path/key.json lm-cloud-sync gcp sync --yes >> /var/log/lm-cloud-sync.log 2>&1

# AWS sync every 6 hours
0 */6 * * * LM_COMPANY=myco LM_ACCESS_ID=xxx LM_ACCESS_KEY=xxx lm-cloud-sync aws sync --yes >> /var/log/lm-cloud-sync-aws.log 2>&1

# Azure sync daily at midnight
0 0 * * * LM_COMPANY=myco LM_BEARER_TOKEN=xxx AZURE_TENANT_ID=xxx AZURE_CLIENT_ID=xxx AZURE_CLIENT_SECRET=xxx lm-cloud-sync azure sync --yes >> /var/log/lm-cloud-sync-azure.log 2>&1
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Sync Cloud Resources to LogicMonitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install lm-cloud-sync
        run: uv tool install lm-cloud-sync

      - name: Sync GCP
        env:
          LM_COMPANY: ${{ secrets.LM_COMPANY }}
          LM_BEARER_TOKEN: ${{ secrets.LM_BEARER_TOKEN }}
          GCP_SA_KEY_PATH: /tmp/sa-key.json
        run: |
          echo '${{ secrets.GCP_SA_KEY }}' > /tmp/sa-key.json
          lm-cloud-sync gcp sync --yes

      - name: Sync AWS
        env:
          LM_COMPANY: ${{ secrets.LM_COMPANY }}
          LM_BEARER_TOKEN: ${{ secrets.LM_BEARER_TOKEN }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: lm-cloud-sync aws sync --yes

      - name: Sync Azure
        env:
          LM_COMPANY: ${{ secrets.LM_COMPANY }}
          LM_BEARER_TOKEN: ${{ secrets.LM_BEARER_TOKEN }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        run: lm-cloud-sync azure sync --yes
```

## Troubleshooting

### LM_BEARER_TOKEN not set

Ensure environment variable is set:

```bash
echo $LM_BEARER_TOKEN
```

If using LMv1 auth, set `LM_ACCESS_ID` and `LM_ACCESS_KEY` instead. Auth method is
auto-detected from which credentials are present.

### Could not find GCP credentials

Verify the service account key path:

```bash
ls -la $GCP_SA_KEY_PATH
```

### Could not find AWS credentials

Verify IAM credentials are set:

```bash
aws sts get-caller-identity
```

Ensure the IAM user has `organizations:ListAccounts` permission on the management account.

### Could not find Azure credentials

Verify Service Principal credentials:

```bash
az login --service-principal -u $AZURE_CLIENT_ID -p $AZURE_CLIENT_SECRET --tenant $AZURE_TENANT_ID
```

### 401 Unauthorized from LogicMonitor

1. Check your bearer token is valid and not expired
2. Verify the token has API access permissions
3. Ensure `LM_COMPANY` matches your portal name exactly
4. If using LMv1, verify `LM_ACCESS_ID` and `LM_ACCESS_KEY` are correct

### 403 Permission Denied from GCP

1. Verify service account has `roles/viewer` on the organization or folder
2. Check the service account key is valid:

```bash
gcloud auth activate-service-account --key-file=$GCP_SA_KEY_PATH
gcloud projects list
```

### No Projects/Accounts/Subscriptions Found

1. Verify the credentials have access to the target resources
2. For GCP: check if projects are in a folder/organization the SA can access
3. For AWS: ensure `organizations:ListAccounts` permission is granted
4. For Azure: ensure the Service Principal has Reader role on the subscriptions

### Azure Resync Fails with Masked Credentials

The LM API masks `secretKey` in GET responses. Provide the real secret:

```bash
lm-cloud-sync azure resync --all --client-secret <your-secret> --yes
```
