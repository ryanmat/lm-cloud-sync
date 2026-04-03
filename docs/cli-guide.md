# LM Cloud Sync - CLI Guide

Command-line tool for discovering cloud resources and syncing them to LogicMonitor.

**Current Version:** v2.0.0 - GCP Support
**Coming Soon:** AWS (v2.1.0), Azure (v2.2.0)

## Overview

| Command | Description |
|---------|-------------|
| `gcp discover` | List all GCP projects accessible by your service account |
| `gcp status` | Compare GCP projects with existing LogicMonitor integrations |
| `gcp sync` | Create LogicMonitor integrations for GCP projects |
| `gcp delete` | Delete a specific LogicMonitor integration |
| `config init` | Create a configuration file template |

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
export LM_BEARER_TOKEN=lmb_xxxxx

# Or use LMv1 authentication
export LM_ACCESS_ID=your-access-id
export LM_ACCESS_KEY=your-access-key

# GCP Service Account Key Path
export GCP_SA_KEY_PATH=/path/to/service-account.json
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

sync:
  dry_run: false
  delete_orphans: false
```

## Command Reference

### gcp discover

Lists all GCP projects accessible by your service account.

```bash
lm-cloud-sync gcp discover

# With auto-discovery (org-level)
lm-cloud-sync gcp discover --auto-discover
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

### gcp status

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

### gcp sync

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

### gcp delete

Delete a specific LogicMonitor integration.

```bash
# Delete by project ID
lm-cloud-sync gcp delete --project-id my-project

# Skip confirmation
lm-cloud-sync gcp delete --project-id my-project --yes
```

### config init

Create a configuration file template.

```bash
# Create config.yaml in current directory
lm-cloud-sync config init

# Specify output path
lm-cloud-sync config init --output /path/to/config.yaml
```

## Scheduling with Cron

Run the sync on a schedule using cron:

```bash
# Edit crontab
crontab -e

# Add entry to sync every hour
0 * * * * LM_COMPANY=myco LM_BEARER_TOKEN=xxx GCP_SA_KEY_PATH=/path/key.json lm-cloud-sync gcp sync --yes >> /var/log/lm-cloud-sync.log 2>&1
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

      - name: Run sync
        env:
          LM_COMPANY: ${{ secrets.LM_COMPANY }}
          LM_BEARER_TOKEN: ${{ secrets.LM_BEARER_TOKEN }}
          GCP_SA_KEY_PATH: /tmp/sa-key.json
        run: |
          echo '${{ secrets.GCP_SA_KEY }}' > /tmp/sa-key.json
          lm-cloud-sync gcp sync --yes
```

## Troubleshooting

### LM_BEARER_TOKEN not set

Ensure environment variable is set:

```bash
echo $LM_BEARER_TOKEN
```

### Could not find GCP credentials

Verify the service account key path:

```bash
ls -la $GCP_SA_KEY_PATH
```

### 401 Unauthorized from LogicMonitor

1. Check your bearer token is valid and not expired
2. Verify the token has API access permissions
3. Ensure `LM_COMPANY` matches your portal name exactly

### 403 Permission Denied from GCP

1. Verify service account has `roles/viewer` on the organization or folder
2. Check the service account key is valid:

```bash
gcloud auth activate-service-account --key-file=$GCP_SA_KEY_PATH
gcloud projects list
```

### No Projects Found

1. Verify the service account has access to projects
2. Check if projects are in a folder/organization the SA can access
3. Try listing projects directly with gcloud
