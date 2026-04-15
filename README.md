# LM Cloud Sync

Multi-cloud automation tool for LogicMonitor integrations.

Automatically discover and sync cloud resources (AWS accounts, Azure subscriptions, GCP projects) to LogicMonitor as device groups.

## Features

- **GCP Support** (v2.0.0): Full support for Google Cloud Platform
  - Auto-discovery using Resource Manager API
  - Project-level integration management
  - 21 GCP services enabled by default
- **Azure Support** (v2.0.5): Full support for Microsoft Azure
  - Auto-discovery using Subscription Management API
  - Subscription-level integration management
  - 42 Azure services enabled by default
- **AWS Support** (v2.1.0): AWS account management
  - Auto-discovery using Organizations API
  - IAM role assumption with external ID support
  - Account-level integration management
- **Cloud Resync**: Trigger LM sync engine on existing integrations
  - Credential re-validation, region re-evaluation, service re-discovery
  - Bulk resync across all integrations per provider
  - Modify regions/services during resync via `--extra-json`
- **CLI & Terraform**: Deploy via command line or infrastructure-as-code
- **Flexible Authentication**: Bearer token or LMv1 auth
- **Dry-run mode**: Preview changes before applying
- **Orphan detection**: Find and clean up stale integrations

## Requirements

- **Python 3.11 or higher** (check with `python3 --version`)
- LogicMonitor API credentials (Bearer token or LMv1)
- Cloud provider credentials:
  - GCP: Service account with Viewer role
  - Azure: Service Principal with Reader role
  - AWS: IAM credentials with `organizations:ListAccounts` permission

## Installation

### Recommended: Using uv or pipx

These tools handle Python version management and avoid system conflicts:

```bash
# Using uv (recommended)
uv tool install lm-cloud-sync

# Or using pipx
pipx install lm-cloud-sync
```

### Alternative: Using pip

If using pip directly, a virtual environment is recommended:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install
pip install lm-cloud-sync
```

> **Note for macOS users:** Direct `pip install` may fail with "externally-managed-environment" error. Use `uv tool install` or `pipx install` instead.

### From Source (For Development)

```bash
# Clone the repository
git clone https://github.com/ryanmat/lm-cloud-sync.git
cd lm-cloud-sync

# Option 1: Run directly with uv
uv run lm-cloud-sync --help

# Option 2: Install in virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
lm-cloud-sync --help

# Option 3: Install as a tool globally
uv tool install --editable .
lm-cloud-sync --help
```

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in your project root (or set environment variables):

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
# LogicMonitor (required for all providers)
LM_COMPANY=your-company-name

# Option A: Bearer token auth
LM_BEARER_TOKEN=your-bearer-token

# Option B: LMv1 auth (access ID + access key)
# LM_ACCESS_ID=your-access-id
# LM_ACCESS_KEY=your-access-key

# Auth method is auto-detected from which credentials are set.

# GCP (if using GCP provider)
GCP_SA_KEY_PATH=/path/to/service-account.json

# AWS (if using AWS provider)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Azure (if using Azure provider)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### 2. Discover GCP Projects

```bash
# Discover GCP projects
lm-cloud-sync gcp discover

# With auto-discovery (org-level)
lm-cloud-sync gcp discover --auto-discover
```

### 3. Check Sync Status

```bash
# Check what's already synced vs what needs to be added
lm-cloud-sync gcp status
```

### 4. Preview Changes (Dry Run)

```bash
# See what would be created without making changes
lm-cloud-sync gcp sync --dry-run
```

### 5. Execute Sync

```bash
# Create integrations in LogicMonitor
lm-cloud-sync gcp sync --yes
```

## CLI Commands

```
lm-cloud-sync
├── gcp               # GCP support
│   ├── discover      # List GCP projects
│   ├── status        # Show sync status
│   ├── sync          # Sync projects to LM
│   ├── delete        # Delete an integration
│   └── resync        # Trigger LM sync engine on existing integrations
├── azure             # Azure support
│   ├── discover      # List Azure subscriptions
│   ├── status        # Show sync status
│   ├── sync          # Sync subscriptions to LM
│   ├── delete        # Delete an integration
│   └── resync        # Trigger LM sync engine (supports --client-secret)
├── aws               # AWS support
│   ├── discover      # List AWS accounts (via Organizations API)
│   ├── status        # Show sync status
│   ├── sync          # Sync accounts to LM
│   ├── delete        # Delete an integration
│   └── resync        # Trigger LM sync engine on existing integrations
└── config
    ├── init          # Create config file
    └── validate      # Validate config
```

### Common Options

```bash
# GCP Examples
lm-cloud-sync gcp discover --auto-discover
lm-cloud-sync gcp status
lm-cloud-sync gcp sync --dry-run
lm-cloud-sync gcp sync --parent-group-id 123 --yes

# Azure Examples
lm-cloud-sync azure discover --auto-discover
lm-cloud-sync azure status
lm-cloud-sync azure sync --dry-run
lm-cloud-sync azure sync --parent-group-id 456 --yes

# AWS Examples
lm-cloud-sync aws discover --auto-discover
lm-cloud-sync aws status
lm-cloud-sync aws sync --auto-discover --dry-run
lm-cloud-sync aws sync --auto-discover --parent-group-id 789 --yes

# Resync existing integrations (triggers LM cloud sync engine)
lm-cloud-sync gcp resync --all --dry-run
lm-cloud-sync aws resync --group-id 1870
lm-cloud-sync azure resync --all --client-secret <secret> --yes

# Delete orphaned integrations
lm-cloud-sync gcp sync --delete-orphans --yes
lm-cloud-sync azure sync --delete-orphans --yes
```

## Configuration

### Environment Variables

**LogicMonitor (Required):**
| Variable | Description |
|----------|-------------|
| `LM_COMPANY` | LogicMonitor portal name |
| `LM_BEARER_TOKEN` | Bearer token for auth |
| `LM_AUTH_METHOD` | Auth method override (`bearer` or `lmv1`). Auto-detected if not set. |
| `LM_ACCESS_ID` | LMv1 access ID (used when auth method is `lmv1`) |
| `LM_ACCESS_KEY` | LMv1 access key (used when auth method is `lmv1`) |

Auth method is auto-detected from which credentials are set. If `LM_BEARER_TOKEN` is
present, Bearer auth is used. If `LM_ACCESS_ID` and `LM_ACCESS_KEY` are present, LMv1
auth is used. Set `LM_AUTH_METHOD` to force a specific method.

**GCP:**
| Variable | Description |
|----------|-------------|
| `GCP_SA_KEY_PATH` | Path to GCP service account JSON |

**AWS:**
| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |

**Azure:**
| Variable | Description |
|----------|-------------|
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Service Principal client ID |
| `AZURE_CLIENT_SECRET` | Service Principal secret |

See [.env.example](.env.example) for all configuration options.

### Configuration File

Create a config file with `lm-cloud-sync config init`:

```yaml
logicmonitor:
  company: "your-company"

gcp:
  enabled: true
  filters:
    exclude_patterns: ["sys-*", "test-*"]
  regions:
    - us-central1
    - us-east1
  services:
    - COMPUTEENGINE
    - CLOUDSQL

sync:
  dry_run: false
  delete_orphans: false
  custom_properties:
    "lm.cloud.managed_by": "lm-cloud-sync"
```

## Terraform

See [terraform/](./terraform/) for Terraform modules (GCP, AWS, Azure).
Terraform modules use bearer token auth and wrap the Python library via `local-exec` provisioners.

```hcl
module "gcp_integrations" {
  source = "github.com/ryanmat/lm-cloud-sync//terraform/modules/gcp"

  lm_company                   = "your-company"
  lm_bearer_token              = var.lm_bearer_token
  gcp_service_account_key_path = "/path/to/service-account.json"

  projects = [
    { project_id = "my-project-1", display_name = "Project 1" },
    { project_id = "my-project-2", display_name = "Project 2" },
  ]
}
```

## Development

```bash
# Clone the repository
git clone https://github.com/ryanmat/lm-cloud-sync.git
cd lm-cloud-sync

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src/

# Run the CLI
uv run lm-cloud-sync --help
```

## Roadmap

- [x] **v2.0.0**: GCP support
- [x] **v2.0.5**: Azure support with Management API discovery
- [x] **v2.1.0**: AWS support with Organizations discovery
- [x] **v2.1.0**: Cloud resync command (triggers LM sync engine via full PUT)
- [x] **v3.0.0**: Auth auto-detect, exit code fixes, cross-provider consistency, security hardening

## License

MIT License - see [LICENSE](./LICENSE) for details.
