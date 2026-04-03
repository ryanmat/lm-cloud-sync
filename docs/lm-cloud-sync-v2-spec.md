# LM Cloud Sync - Multi-Cloud Technical Specification

## Document Information
- **Version**: 2.0.0
- **Created**: 2025-01-29 (v1.0 - GCP only)
- **Updated**: 2025-12-01 (v2.0 - Multi-cloud)
- **Status**: Active - Published to PyPI
- **Repository**: `lm-cloud-sync` (standalone)
- **PyPI**: https://pypi.org/project/lm-cloud-sync/
- **Current Release**: v2.0.0 (GCP support), AWS/Azure in development

---

## 1. Executive Summary

### 1.1 Problem Statement
LogicMonitor's cloud integrations require separate configuration for each cloud account/project/subscription. For enterprise customers managing hundreds of cloud resources across AWS, Azure, and GCP, manual onboarding is impractical.

### 1.2 Solution Overview
A unified multi-cloud automation tool that discovers cloud resources and creates LogicMonitor integrations:

| Cloud | Discovery Source | LM Integration Type |
|-------|------------------|---------------------|
| **AWS** | Organizations / Accounts | `AWS/AwsRoot` device group |
| **Azure** | Management Groups / Subscriptions | `Azure/AzureRoot` device group |
| **GCP** | Resource Manager / Projects | `GCP/GcpRoot` device group |

### 1.3 Key Features
- **Unified CLI**: Single tool for all three clouds
- **Selective Sync**: Choose one cloud, multiple clouds, or all
- **Two Deployment Options**: CLI and Terraform
- **Auto-Discovery**: Optional organization-level discovery (AWS Organizations, Azure Management Groups, GCP folders)
- **Dry-Run Mode**: Preview changes before applying
- **Orphan Handling**: Configurable cleanup of removed cloud resources

### 1.4 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-29 | Initial GCP-only implementation |
| 2.0.0 | 2025-12-01 | Multi-cloud support (AWS, Azure, GCP) |

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           LM Cloud Sync v2.0 Architecture                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                          Core Library (lm_cloud_sync)                       │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │ │
│  │  │   LM Client     │  │   Config        │  │   Models        │            │ │
│  │  │   (Shared)      │  │   Manager       │  │   (Shared)      │            │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                         Provider Interface                           │  │ │
│  │  │                                                                      │  │ │
│  │  │    discover() -> List[CloudResource]                                │  │ │
│  │  │    list_integrations() -> List[LMGroup]                             │  │ │
│  │  │    create_integration(resource) -> LMGroup                          │  │ │
│  │  │    delete_integration(group_id) -> None                             │  │ │
│  │  │                                                                      │  │ │
│  │  └─────────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│              ┌─────────────────────────┼─────────────────────────┐              │
│              │                         │                         │              │
│              ▼                         ▼                         ▼              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐     │
│  │   AWS Provider      │  │   Azure Provider    │  │   GCP Provider      │     │
│  │                     │  │                     │  │                     │     │
│  │  - Organizations    │  │  - Management       │  │  - Resource         │     │
│  │  - STS / IAM Role   │  │    Groups           │  │    Manager          │     │
│  │  - External ID      │  │  - Service          │  │  - Service          │     │
│  │                     │  │    Principal        │  │    Account          │     │
│  │  groupType:         │  │                     │  │                     │     │
│  │  AWS/AwsRoot        │  │  groupType:         │  │  groupType:         │     │
│  │                     │  │  Azure/AzureRoot    │  │  GCP/GcpRoot        │     │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘     │
│              │                         │                         │              │
│              ▼                         ▼                         ▼              │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          Deployment Options                              │   │
│  │                                                                          │   │
│  │  ┌───────────────────────────────┐     ┌───────────────────────────┐   │   │
│  │  │           CLI                 │     │        Terraform          │   │   │
│  │  │                               │     │                           │   │   │
│  │  │  lm-cloud-sync aws sync       │     │  modules/                 │   │   │
│  │  │  lm-cloud-sync azure sync     │     │    aws/                   │   │   │
│  │  │  lm-cloud-sync gcp sync       │     │    azure/                 │   │   │
│  │  │  lm-cloud-sync all sync       │     │    gcp/                   │   │   │
│  │  │                               │     │                           │   │   │
│  │  │  Flags:                       │     │  Features:                │   │   │
│  │  │  --auto-discover              │     │  - State management       │   │   │
│  │  │  --dry-run                    │     │  - Plan/Apply workflow    │   │   │
│  │  │  --delete-orphans             │     │  - Orphan cleanup         │   │   │
│  │  └───────────────────────────────┘     └───────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Provider Abstraction

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class CloudProvider(ABC):
    """Abstract base class for cloud providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (aws, azure, gcp)."""
        pass

    @property
    @abstractmethod
    def group_type(self) -> str:
        """LogicMonitor groupType value."""
        pass

    @abstractmethod
    def discover(self) -> List[CloudResource]:
        """Discover cloud resources (accounts/subscriptions/projects)."""
        pass

    @abstractmethod
    def list_integrations(self, client: LogicMonitorClient) -> List[LMCloudGroup]:
        """List existing LM integrations for this provider."""
        pass

    @abstractmethod
    def create_integration(
        self,
        client: LogicMonitorClient,
        resource: CloudResource,
        **kwargs
    ) -> LMCloudGroup:
        """Create LM integration for a cloud resource."""
        pass

    @abstractmethod
    def delete_integration(
        self,
        client: LogicMonitorClient,
        group_id: int
    ) -> None:
        """Delete LM integration."""
        pass
```

---

## 3. Cloud Provider Specifications

### 3.1 AWS Provider

#### 3.1.1 Authentication
```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Authentication Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Get External ID from LM                                │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  GET /aws/externalId                                    │     │
│  │  Response: { "externalId": "abc123..." }               │     │
│  │  (Valid for 1 hour, same user must complete step 2)    │     │
│  └────────────────────────────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│  Step 2: Create IAM Cross-Account Role in AWS                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Trust Policy:                                          │     │
│  │  {                                                      │     │
│  │    "Principal": {                                       │     │
│  │      "AWS": "arn:aws:iam::282028653949:root"           │     │
│  │    },                                                   │     │
│  │    "Condition": {                                       │     │
│  │      "StringEquals": {                                  │     │
│  │        "sts:ExternalId": "abc123..."                   │     │
│  │      }                                                  │     │
│  │    }                                                    │     │
│  │  }                                                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│  Step 3: Create LM Integration                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  POST /device/groups                                    │     │
│  │  {                                                      │     │
│  │    "groupType": "AWS/AwsRoot",                         │     │
│  │    "extra": {                                           │     │
│  │      "account": {                                       │     │
│  │        "assumedRoleArn": "arn:aws:iam::ACCOUNT:role/X",│     │
│  │        "externalId": "abc123..."                       │     │
│  │      }                                                  │     │
│  │    }                                                    │     │
│  │  }                                                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 Discovery
```python
# AWS Account Discovery using Organizations API
import boto3

def discover_aws_accounts() -> List[AWSAccount]:
    org_client = boto3.client('organizations')
    accounts = []

    paginator = org_client.get_paginator('list_accounts')
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE':
                accounts.append(AWSAccount(
                    account_id=account['Id'],
                    account_name=account['Name'],
                    email=account['Email'],
                    status=account['Status'],
                ))

    return accounts
```

#### 3.1.3 LM API Payload
```json
{
  "parentId": 1,
  "name": "AWS - 123456789012",
  "description": "AWS Account: Production",
  "groupType": "AWS/AwsRoot",
  "extra": {
    "account": {
      "assumedRoleArn": "arn:aws:iam::123456789012:role/LogicMonitorRole",
      "externalId": "lm-external-id-abc123",
      "collectorId": -2,
      "schedule": "0 * * * *"
    },
    "default": {
      "useDefault": true,
      "selectAll": false,
      "monitoringRegions": ["us-east-1", "us-west-2"],
      "deadOperation": "KEEP_7_DAYS",
      "disableTerminatedHostAlerting": true
    },
    "services": {
      "EC2": { ... },
      "RDS": { ... },
      "S3": { ... }
    }
  }
}
```

### 3.2 Azure Provider

#### 3.2.1 Authentication
```
┌─────────────────────────────────────────────────────────────────┐
│                   Azure Authentication Flow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Service Principal with Reader Role                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Required Information:                                  │     │
│  │  - Tenant ID (Directory ID)                            │     │
│  │  - Client ID (Application ID)                          │     │
│  │  - Client Secret                                        │     │
│  │  - Subscription ID(s)                                   │     │
│  └────────────────────────────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│  LM Integration Payload                                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  POST /device/groups                                    │     │
│  │  {                                                      │     │
│  │    "groupType": "Azure/AzureRoot",                     │     │
│  │    "extra": {                                           │     │
│  │      "account": {                                       │     │
│  │        "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxx",      │     │
│  │        "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxx",      │     │
│  │        "secretKey": "xxxxxxxxxxxxxxxxxxxxxxxx",         │     │
│  │        "subscriptionIds": "sub-id-1,sub-id-2"          │     │
│  │      }                                                  │     │
│  │    }                                                    │     │
│  │  }                                                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Discovery
```python
# Azure Subscription Discovery
from azure.identity import DefaultAzureCredential
from azure.mgmt.subscription import SubscriptionClient

def discover_azure_subscriptions() -> List[AzureSubscription]:
    credential = DefaultAzureCredential()
    client = SubscriptionClient(credential)
    subscriptions = []

    for sub in client.subscriptions.list():
        if sub.state == 'Enabled':
            subscriptions.append(AzureSubscription(
                subscription_id=sub.subscription_id,
                display_name=sub.display_name,
                tenant_id=sub.tenant_id,
                state=sub.state,
            ))

    return subscriptions
```

#### 3.2.3 LM API Payload
```json
{
  "parentId": 1,
  "name": "Azure - Production Subscription",
  "description": "Azure Subscription",
  "groupType": "Azure/AzureRoot",
  "extra": {
    "account": {
      "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "secretKey": "client-secret-value",
      "subscriptionIds": "sub-id-1,sub-id-2",
      "collectorId": -2,
      "schedule": "0 * * * *"
    },
    "default": {
      "useDefault": true,
      "selectAll": false,
      "monitoringRegions": ["eastus", "westus2"],
      "deadOperation": "KEEP_7_DAYS",
      "disableTerminatedHostAlerting": true
    },
    "services": {
      "VIRTUALMACHINE": { ... },
      "SQLDATABASE": { ... },
      "STORAGEACCOUNT": { ... }
    }
  }
}
```

### 3.3 GCP Provider (Existing v1.0)

#### 3.3.1 Authentication
- Service Account Key JSON
- Viewer role at organization/folder/project level

#### 3.3.2 Discovery
- Resource Manager API: `projects.search()`

#### 3.3.3 LM API Payload
```json
{
  "parentId": 1,
  "name": "GCP - my-project-id",
  "groupType": "GCP/GcpRoot",
  "extra": {
    "account": {
      "projectId": "my-project-id",
      "serviceAccountKey": { ... },
      "collectorId": -2,
      "schedule": "0 * * * *"
    },
    "services": {
      "COMPUTEENGINE": { ... },
      "CLOUDSQL": { ... }
    }
  }
}
```

---

## 4. Data Models

### 4.1 Shared Models

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

@dataclass
class CloudResource:
    """Base class for cloud resources."""
    provider: CloudProvider
    resource_id: str           # Account ID, Subscription ID, or Project ID
    display_name: str
    status: str
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class AWSAccount(CloudResource):
    provider: CloudProvider = CloudProvider.AWS
    email: Optional[str] = None
    arn: Optional[str] = None

@dataclass
class AzureSubscription(CloudResource):
    provider: CloudProvider = CloudProvider.AZURE
    tenant_id: Optional[str] = None

@dataclass
class GCPProject(CloudResource):
    provider: CloudProvider = CloudProvider.GCP
    project_number: Optional[str] = None
    parent: Optional[str] = None

@dataclass
class LMCloudGroup:
    """LogicMonitor cloud integration group."""
    id: int
    name: str
    provider: CloudProvider
    resource_id: str           # AWS Account ID, Azure Sub ID, or GCP Project ID
    parent_id: int = 1
    description: str = ""
    custom_properties: Dict[str, str] = field(default_factory=dict)
```

### 4.2 Configuration Model

```python
@dataclass
class ProviderConfig:
    """Configuration for a single cloud provider."""
    enabled: bool = True
    parent_group_id: int = 1
    regions: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Config:
    """Main configuration."""
    logicmonitor: LMConfig
    aws: Optional[ProviderConfig] = None
    azure: Optional[ProviderConfig] = None
    gcp: Optional[ProviderConfig] = None
    sync: SyncConfig = field(default_factory=SyncConfig)
```

---

## 5. CLI Interface

### 5.1 Command Structure

```
lm-cloud-sync
├── aws
│   ├── discover          # List AWS accounts
│   ├── status            # Show sync status
│   └── sync              # Sync AWS accounts to LM
├── azure
│   ├── discover          # List Azure subscriptions
│   ├── status            # Show sync status
│   └── sync              # Sync Azure subscriptions to LM
├── gcp
│   ├── discover          # List GCP projects
│   ├── status            # Show sync status
│   └── sync              # Sync GCP projects to LM
├── all
│   ├── discover          # Discover all clouds
│   ├── status            # Show all sync status
│   └── sync              # Sync all clouds
└── config
    ├── init              # Initialize configuration
    └── validate          # Validate configuration
```

### 5.2 Discovery Modes

**Explicit Mode (Default)**: Resources defined in config file
```yaml
# config.yaml
aws:
  accounts:
    - account_id: "123456789012"
      role_arn: "arn:aws:iam::123456789012:role/LogicMonitorRole"
    - account_id: "234567890123"
      role_arn: "arn:aws:iam::234567890123:role/LogicMonitorRole"
```

**Auto-Discovery Mode**: Discover resources at organization level
```bash
# AWS - Uses AWS Organizations API
lm-cloud-sync aws discover --auto-discover
lm-cloud-sync aws sync --auto-discover

# Azure - Lists subscriptions accessible to Service Principal
lm-cloud-sync azure discover --auto-discover
lm-cloud-sync azure sync --auto-discover

# GCP - Uses Resource Manager to search projects
lm-cloud-sync gcp discover --auto-discover
lm-cloud-sync gcp sync --auto-discover
```

**Permissions Required for Auto-Discovery:**

| Cloud | API/Permission Required |
|-------|------------------------|
| AWS | `organizations:ListAccounts` on management account |
| Azure | `Reader` role on Management Group or Tenant root |
| GCP | `resourcemanager.projects.list` on org/folder |

### 5.3 Dry-Run and Orphan Handling

**Dry-Run Mode**: Preview changes without executing
```bash
# Shows what would be created/updated/deleted
lm-cloud-sync aws sync --dry-run
lm-cloud-sync all sync --auto-discover --dry-run
```

**Orphan Handling**: When cloud resources are removed
```bash
# Show orphaned LM groups (exist in LM but not in cloud)
lm-cloud-sync aws status --show-orphans

# Delete orphaned groups during sync
lm-cloud-sync aws sync --delete-orphans

# Combine with dry-run to preview deletions
lm-cloud-sync all sync --delete-orphans --dry-run
```

**Orphan Handling Strategies:**
| Option | Behavior |
|--------|----------|
| `--delete-orphans` | Delete LM groups for removed cloud resources |
| (default) | Keep orphans, warn in status output |

### 5.4 Usage Examples

```bash
# Discover resources (explicit config)
lm-cloud-sync aws discover
lm-cloud-sync azure discover
lm-cloud-sync gcp discover
lm-cloud-sync all discover

# Discover resources (auto-discovery)
lm-cloud-sync aws discover --auto-discover
lm-cloud-sync all discover --auto-discover

# Check status (with orphan detection)
lm-cloud-sync aws status
lm-cloud-sync all status --show-orphans

# Sync with dry-run (always recommended first)
lm-cloud-sync aws sync --dry-run
lm-cloud-sync all sync --auto-discover --dry-run

# Sync (execute)
lm-cloud-sync gcp sync --yes
lm-cloud-sync all sync --yes

# Sync with orphan cleanup
lm-cloud-sync aws sync --delete-orphans --yes
lm-cloud-sync all sync --auto-discover --delete-orphans --yes

# Selective sync (specific providers only)
lm-cloud-sync all sync --providers aws,gcp --yes
```

### 5.5 Output Examples

```
$ lm-cloud-sync all discover

Discovering cloud resources...

AWS Accounts (3 found):
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Account ID   ┃ Name               ┃ Status   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 123456789012 │ Production         │ ACTIVE   │
│ 234567890123 │ Development        │ ACTIVE   │
│ 345678901234 │ Sandbox            │ ACTIVE   │
└──────────────┴────────────────────┴──────────┘

Azure Subscriptions (2 found):
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Subscription ID                       ┃ Name               ┃ Status   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx │ Prod Subscription  │ Enabled  │
│ yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy │ Dev Subscription   │ Enabled  │
└──────────────────────────────────────┴────────────────────┴──────────┘

GCP Projects (4 found):
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Project ID                 ┃ Display Name            ┃ Status   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ project-alpha              │ Project Alpha           │ ACTIVE   │
│ project-beta               │ Project Beta            │ ACTIVE   │
│ project-gamma              │ Project Gamma           │ ACTIVE   │
│ project-delta              │ Project Delta           │ ACTIVE   │
└────────────────────────────┴─────────────────────────┴──────────┘

Total: 9 cloud resources discovered
```

---

## 6. Repository Structure

```
lm-cloud-sync/
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
│
├── src/
│   └── lm_cloud_sync/
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py              # CLI entry point
│       │   ├── aws_cmd.py           # AWS commands
│       │   ├── azure_cmd.py         # Azure commands
│       │   ├── gcp_cmd.py           # GCP commands
│       │   └── all_cmd.py           # Multi-cloud commands
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── lm_client.py         # LogicMonitor API client
│       │   ├── config.py            # Configuration management
│       │   ├── models.py            # Shared data models
│       │   ├── sync.py              # Sync orchestration
│       │   └── exceptions.py        # Exception hierarchy
│       │
│       └── providers/
│           ├── __init__.py
│           ├── base.py              # Abstract provider interface
│           │
│           ├── aws/
│           │   ├── __init__.py
│           │   ├── discovery.py     # AWS Organizations/Accounts
│           │   ├── groups.py        # LM AWS group operations
│           │   └── auth.py          # IAM role / external ID
│           │
│           ├── azure/
│           │   ├── __init__.py
│           │   ├── discovery.py     # Azure subscriptions
│           │   ├── groups.py        # LM Azure group operations
│           │   └── auth.py          # Service principal
│           │
│           └── gcp/
│               ├── __init__.py
│               ├── discovery.py     # GCP projects
│               ├── groups.py        # LM GCP group operations
│               └── auth.py          # Service account
│
├── terraform/
│   ├── modules/
│   │   ├── aws/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── scripts/
│   │   │       ├── create_integration.py
│   │   │       └── delete_integration.py
│   │   ├── azure/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── scripts/
│   │   │       └── ...
│   │   └── gcp/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── scripts/
│   │   │       └── ...
│   │   └── all/                    # Multi-cloud module
│   │       ├── main.tf
│   │       └── variables.tf
│   └── examples/
│       ├── aws-only/
│       ├── azure-only/
│       ├── gcp-only/
│       └── multi-cloud/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_lm_client.py
│   │   ├── test_aws_provider.py
│   │   ├── test_azure_provider.py
│   │   └── test_gcp_provider.py
│   └── integration/
│       └── ...
│
├── docs/
│   ├── getting-started.md
│   ├── aws-guide.md
│   ├── azure-guide.md
│   ├── gcp-guide.md
│   ├── terraform-guide.md
│   ├── cli-reference.md
│   └── troubleshooting.md
│
└── examples/
    ├── config.yaml.example
    └── ...
```

---

## 7. Configuration

### 7.1 Configuration File (`config.yaml`)

```yaml
# LogicMonitor settings (shared across all providers)
logicmonitor:
  company: "your-company"
  # Credentials from environment: LM_BEARER_TOKEN or LM_ACCESS_ID/KEY

# AWS Configuration
aws:
  enabled: true
  parent_group_id: 100           # LM parent group for AWS integrations

  # IAM Role settings
  role_name: "LogicMonitorRole"  # Role name to assume in each account

  # Discovery filters
  filters:
    include_accounts: []         # Empty = all accounts
    exclude_accounts:
      - "999999999999"           # Exclude specific accounts
    required_tags:
      Environment: "production"

  # Monitoring settings
  regions:
    - us-east-1
    - us-west-2
  services:
    - EC2
    - RDS
    - S3
    - Lambda

# Azure Configuration
azure:
  enabled: true
  parent_group_id: 200

  # Service Principal (from environment or config)
  # AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET

  filters:
    include_subscriptions: []
    exclude_subscriptions: []

  regions:
    - eastus
    - westus2
  services:
    - VIRTUALMACHINE
    - SQLDATABASE
    - STORAGEACCOUNT

# GCP Configuration
gcp:
  enabled: true
  parent_group_id: 300

  # Service account key path or GOOGLE_APPLICATION_CREDENTIALS
  service_account_key_path: null

  filters:
    include_projects: []
    exclude_projects:
      - "sys-*"
    required_labels:
      managed: "true"

  regions:
    - us-central1
    - us-east1
  services:
    - COMPUTEENGINE
    - CLOUDSQL

# Sync behavior
sync:
  dry_run: false                   # Preview mode (no changes made)
  auto_discover: false             # Use org-level discovery APIs
  create_missing: true             # Create LM groups for new cloud resources
  update_existing: false           # Update existing LM groups
  delete_orphans: false            # Delete LM groups for removed cloud resources

  # Custom properties added to all integrations
  custom_properties:
    "lm.cloud.managed_by": "lm-cloud-sync"
    "lm.cloud.version": "2.0.0"
```

### 7.2 Environment Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `LM_COMPANY` | All | LogicMonitor portal name |
| `LM_BEARER_TOKEN` | All | LogicMonitor Bearer token |
| `AWS_ACCESS_KEY_ID` | AWS | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS | AWS credentials |
| `AWS_SESSION_TOKEN` | AWS | AWS session token (optional) |
| `AZURE_TENANT_ID` | Azure | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Azure | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Azure | Service principal secret |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP | Path to service account key |

---

## 8. Migration Path (v1.0 → v2.0)

### 8.1 Phase 1: Foundation
- Create new `lm-cloud-sync` repository
- Refactor GCP code into provider pattern
- Ensure backward compatibility with existing GCP configs
- Add dry-run mode and orphan handling

### 8.2 Phase 2: AWS Support
- Implement AWS provider
- Add IAM role setup automation
- External ID management
- Auto-discovery via AWS Organizations

### 8.3 Phase 3: Azure Support
- Implement Azure provider
- Service principal management
- Management group auto-discovery

### 8.4 Phase 4: Polish
- Multi-cloud CLI (`lm-cloud-sync all`)
- Terraform modules for all providers
- Comprehensive documentation and testing

---

## 9. Security Considerations

### 9.1 Credential Management

| Provider | Credential Type | Recommended Storage |
|----------|-----------------|---------------------|
| LogicMonitor | Bearer Token | Environment variable |
| AWS | IAM Role ARN | Config file (not secret) |
| AWS | External ID | Retrieved from LM API |
| Azure | Service Principal | Environment variables |
| GCP | Service Account Key | Secret Manager or file |

### 9.2 Least Privilege

**AWS IAM Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "s3:GetBucket*",
        "s3:List*",
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

**Azure Service Principal:**
- `Reader` role at subscription or management group level

**GCP Service Account:**
- `roles/viewer` at organization, folder, or project level

---

## 10. Testing Strategy

### 10.1 Test Matrix

| Provider | Unit Tests | Integration Tests | E2E Tests |
|----------|-----------|-------------------|-----------|
| Core/LM Client | Mock HTTP (httpx) | Real LM API (sandbox portal) | - |
| AWS | Mock boto3 | LocalStack | Real AWS (optional) |
| Azure | Mock SDK | - | Real Azure (optional) |
| GCP | Mock SDK | - | Real GCP (optional) |
| CLI | pytest + Click testing | - | Full command tests |
| Terraform | - | terraform validate | terraform plan (dry) |

### 10.2 Unit Testing Approach

**Mock HTTP Responses**: Use `pytest-httpx` to mock LM API calls
```python
# tests/unit/test_lm_client.py
import pytest
from pytest_httpx import HTTPXMock

def test_create_aws_group(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://company.logicmonitor.com/santaba/rest/device/groups",
        method="POST",
        json={"id": 123, "name": "AWS - 123456789012"},
    )

    client = LogicMonitorClient(company="company", bearer_token="token")
    result = client.post("device/groups", json={...})
    assert result["id"] == 123
```

**Mock Cloud SDKs**: Use `moto` for AWS, `unittest.mock` for Azure/GCP
```python
# tests/unit/test_aws_discovery.py
from moto import mock_aws

@mock_aws
def test_discover_aws_accounts():
    # moto provides fake AWS Organizations
    org = boto3.client("organizations")
    org.create_organization(FeatureSet="ALL")
    org.create_account(Email="test@example.com", AccountName="Test")

    accounts = discover_aws_accounts()
    assert len(accounts) == 1
```

### 10.3 Integration Testing

**LM API Integration** (requires sandbox portal):
```python
# tests/integration/test_lm_api.py
@pytest.mark.integration
def test_list_gcp_groups_real_api():
    """Test against real LM sandbox portal."""
    client = LogicMonitorClient(
        company=os.environ["LM_COMPANY"],
        bearer_token=os.environ["LM_BEARER_TOKEN"],
    )
    groups = list_gcp_groups(client)
    assert isinstance(groups, list)
```

**LocalStack for AWS** (simulates AWS locally):
```yaml
# docker-compose.yml for LocalStack
services:
  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=organizations,sts
```

### 10.4 CLI Testing

**Click Testing Utilities**:
```python
# tests/unit/test_cli.py
from click.testing import CliRunner
from lm_cloud_sync.cli.main import cli

def test_discover_command_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["aws", "discover", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output

def test_sync_requires_confirmation():
    runner = CliRunner()
    result = runner.invoke(cli, ["gcp", "sync"])  # No --yes flag
    assert "Are you sure?" in result.output
```

### 10.5 Terraform Testing

**Validation**:
```bash
# Syntax and configuration validation
terraform -chdir=terraform/modules/aws validate
terraform -chdir=terraform/modules/azure validate
terraform -chdir=terraform/modules/gcp validate
```

**Dry-Run Plans**:
```bash
# Generate plan without applying
terraform -chdir=terraform/examples/aws-only plan -out=tfplan
```

### 10.6 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --cov=lm_cloud_sync

      - name: Run integration tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          LM_COMPANY: ${{ secrets.LM_COMPANY }}
          LM_BEARER_TOKEN: ${{ secrets.LM_BEARER_TOKEN }}
        run: uv run pytest tests/integration/ -v -m integration

      - name: Lint
        run: uv run ruff check src/

      - name: Type check
        run: uv run mypy src/

      - name: Validate Terraform
        run: |
          cd terraform/modules/aws && terraform init -backend=false && terraform validate
          cd ../azure && terraform init -backend=false && terraform validate
          cd ../gcp && terraform init -backend=false && terraform validate

  localstack:
    runs-on: ubuntu-latest
    services:
      localstack:
        image: localstack/localstack
        ports:
          - 4566:4566
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Run AWS tests with LocalStack
        env:
          AWS_ENDPOINT_URL: http://localhost:4566
          AWS_ACCESS_KEY_ID: test
          AWS_SECRET_ACCESS_KEY: test
        run: uv run pytest tests/integration/test_aws*.py -v
```

### 10.7 Test Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Core/LM Client | 90% |
| Providers | 85% |
| CLI Commands | 80% |
| Config Loading | 90% |
| Overall | 85% |

---

## 11. Rate Limiting

### 11.1 API Rate Limits

| Service | Rate Limit | Mitigation |
|---------|-----------|------------|
| LogicMonitor REST API | Varies by endpoint (~100 req/min typical) | Exponential backoff, batch operations |
| AWS Organizations | 10 requests/second | Built-in boto3 retry |
| AWS STS AssumeRole | 100 requests/second per account | Generally not an issue |
| Azure Resource Manager | 12000 reads/hour per subscription | Pagination, caching |
| GCP Resource Manager | 300 queries/minute | Exponential backoff |

### 11.2 Implementation Considerations

**Concurrency Control**:
```python
# Max concurrent API calls per provider
MAX_CONCURRENT_LM_CALLS = 10
MAX_CONCURRENT_AWS_CALLS = 5
MAX_CONCURRENT_AZURE_CALLS = 5
MAX_CONCURRENT_GCP_CALLS = 5
```

**Retry Strategy**:
```python
# Exponential backoff with jitter
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,      # seconds
    "max_delay": 30.0,      # seconds
    "exponential_base": 2,
    "jitter": True,
}
```

**Batch Processing** (for large organizations):
- AWS: Process accounts in batches of 50
- Azure: Process subscriptions in batches of 50
- GCP: Process projects in batches of 100
- Progress reporting for long-running syncs

### 11.3 Recommendations for Large Deployments

| Scenario | Recommendation |
|----------|---------------|
| < 50 cloud resources | Default settings work fine |
| 50-200 cloud resources | Increase timeouts, use `--verbose` to monitor |
| 200+ cloud resources | Run in batches, consider scheduling overnight |

---

## 12. Technical Debt / Future Enhancements

### 12.1 Planned for Future Releases

| Feature | Priority | Description |
|---------|----------|-------------|
| Dashboard/Reporting | Medium | Web UI showing sync status across all clouds |
| Credential Rotation | Medium | Support for rotating service account keys without downtime |
| Parallel Sync | Low | Sync multiple clouds simultaneously |
| State File | Low | Local state file to track sync status between runs |

### 12.2 Credential Rotation Ideas

**GCP Service Account Key Rotation**:
- Support multiple keys in rotation
- Validate new key before removing old
- Integration with GCP Secret Manager

**Azure Service Principal**:
- Support for certificate-based auth
- Azure Key Vault integration

**AWS IAM Roles**:
- Roles don't require rotation
- External ID refresh via LM API

### 12.3 Dashboard Considerations (Future)

If dashboard is added, consider:
- Read-only status view (no sync actions from UI)
- Sync history and logs
- Orphan detection summary
- Integration with existing LM portal (if possible)

---

## 13. References

- [LogicMonitor REST API - AWS Device Groups](https://www.logicmonitor.com/support/rest-api-developers-guide/v1/device-groups/aws-device-groups)
- [LogicMonitor REST API - Azure Device Groups](https://www.logicmonitor.com/support/rest-api-developers-guide/v1/device-groups/azure-device-groups)
- [LogicMonitor REST API - GCP Device Groups](https://www.logicmonitor.com/support/rest-api-developers-guide/v1/device-groups/gcp-device-groups)
- [AWS Organizations API](https://docs.aws.amazon.com/organizations/latest/APIReference/Welcome.html)
- [Azure Subscription Client](https://learn.microsoft.com/en-us/python/api/azure-mgmt-subscription/)
- [GCP Resource Manager API](https://cloud.google.com/resource-manager/reference/rest)
