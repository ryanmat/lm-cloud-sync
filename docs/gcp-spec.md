# GCP Multi-Project Monitoring Solution - Technical Specification

## Document Information
- **Version**: 1.0.0
- **Created**: 2025-01-29
- **Status**: Superseded by lm-cloud-sync-v2-spec.md

Note: This document describes the original GCP-only implementation. See lm-cloud-sync-v2-spec.md for the current multi-cloud architecture.

---

## 1. Executive Summary

### 1.1 Problem Statement
LogicMonitor's GCP integration requires a separate integration for each GCP project, unlike AWS which supports Organization-level onboarding. For customers with 60+ projects, manually adding each project is impractical.

### 1.2 Solution Overview
A three-tiered automation solution:
- **Option 1**: Python CLI tool for bulk project onboarding
- **Option 2**: Terraform module for GitOps-managed onboarding
- **Option 3**: GCP Cloud Function for real-time, event-driven onboarding

### 1.3 Scope
- Initial POC using dev environment
- GCP Project: `my-gcp-project` (123456789000)
- LogicMonitor portal: Dev/sandbox environment

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Solution Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Shared Python Library                         │   │
│  │                         (lm-gcp-integration)                         │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  LM API      │  │  GCP Project │  │  GCP Group   │              │   │
│  │  │  Client      │  │  Discovery   │  │  Builder     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  Config      │  │  Logging     │  │  Exceptions  │              │   │
│  │  │  Manager     │  │  Utils       │  │  & Errors    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐             │
│          │                         │                         │             │
│          ▼                         ▼                         ▼             │
│  ┌───────────────┐        ┌───────────────┐        ┌───────────────┐      │
│  │   Option 1    │        │   Option 2    │        │   Option 3    │      │
│  │   CLI Tool    │        │   Terraform   │        │ Cloud Function│      │
│  │               │        │               │        │               │      │
│  │  - Bulk add   │        │  - IaC mgmt   │        │  - Event-     │      │
│  │  - Sync       │        │  - GitOps     │        │    driven     │      │
│  │  - Report     │        │  - CI/CD      │        │  - Real-time  │      │
│  └───────────────┘        └───────────────┘        └───────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Descriptions

#### 2.2.1 Shared Python Library (`lm_gcp_integration`)

| Component | Responsibility |
|-----------|----------------|
| `lm_client.py` | LogicMonitor REST API client with Bearer token and LMv1 authentication |
| `gcp_discovery.py` | Enumerate GCP projects using Resource Manager API |
| `gcp_group_builder.py` | Construct GCP device group JSON payloads for LM API |
| `config.py` | Configuration loading from YAML and environment variables |
| `exceptions.py` | Custom exception hierarchy |
| `models.py` | Data models (Project, GCPGroup, MonitoringConfig) |

#### 2.2.2 Option 1: CLI Tool (`lm-gcp-sync`)

Command-line interface for manual or scheduled execution:
```bash
lm-gcp-sync discover              # List GCP projects
lm-gcp-sync sync --dry-run        # Preview changes
lm-gcp-sync sync                  # Execute sync
lm-gcp-sync report                # Generate status report
```

#### 2.2.3 Option 2: Terraform Module

Terraform-managed GCP integrations:
```hcl
module "lm_gcp_projects" {
  source = "./modules/lm-gcp-integration"
  
  projects         = local.gcp_projects
  lm_company       = var.lm_company
  parent_group_id  = var.lm_parent_group_id
}
```

#### 2.2.4 Option 3: Cloud Function

Event-driven sync triggered by GCP project lifecycle events:
- Pub/Sub topic receives project create/delete events
- Cloud Function processes events and calls LM API
- Dead letter queue for failed processing

---

## 3. Data Models

### 3.1 GCP Project

```python
@dataclass
class GCPProject:
    project_id: str           # e.g., "my-gcp-project"
    project_number: str       # e.g., "123456789000"
    display_name: str         # Human-readable name
    state: str                # ACTIVE, DELETE_REQUESTED, etc.
    parent: Optional[str]     # Folder or organization ID
    labels: Dict[str, str]    # GCP labels
    create_time: datetime
```

### 3.2 LogicMonitor GCP Group

```python
@dataclass
class LMGCPGroup:
    id: Optional[int]                    # LM group ID (None if not created)
    name: str                            # Display name in LM
    parent_id: int                       # Parent group ID
    project_id: str                      # GCP project ID
    description: str
    custom_properties: Dict[str, str]
    monitoring_config: MonitoringConfig
```

### 3.3 Monitoring Configuration

```python
@dataclass
class MonitoringConfig:
    netscan_frequency: str = "0 * * * *"  # Cron format
    dead_operation: str = "KEEP_7_DAYS"   # MANUALLY, KEEP_7_DAYS, etc.
    disable_terminated_alerting: bool = True
    regions: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    tags: List[TagFilter] = field(default_factory=list)
```

---

## 4. API Specifications

### 4.1 LogicMonitor REST API

#### 4.1.1 Authentication

**Bearer Token (Primary)**
```http
Authorization: Bearer lmb_your_bearer_token_here
```

**LMv1 Signature (Fallback)**
```http
Authorization: LMv1 {access_id}:{signature}:{epoch}
```

Signature calculation:
```python
request_vars = f"{http_method}{epoch}{data}{resource_path}"
signature = base64.b64encode(
    hmac.new(
        access_key.encode(),
        request_vars.encode(),
        hashlib.sha256
    ).hexdigest().encode()
).decode()
```

#### 4.1.2 Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/device/groups` | List all device groups |
| GET | `/device/groups?filter=groupType:"GCP/GcpRoot"` | List GCP integrations |
| POST | `/device/groups` | Create new GCP integration |
| PUT | `/device/groups/{id}` | Update GCP integration |
| DELETE | `/device/groups/{id}` | Delete GCP integration |

#### 4.1.3 GCP Group Payload Structure

```json
{
  "parentId": 1,
  "name": "GCP - my-gcp-project",
  "description": "Auto-managed GCP project",
  "groupType": "GCP/GcpRoot",
  "customProperties": [
    {"name": "lm.gcp.auto_managed", "value": "true"},
    {"name": "lm.gcp.sync_version", "value": "1.0.0"}
  ],
  "extra": {
    "account": {
      "projectId": "my-gcp-project",
      "collectorId": -2,
      "schedule": "0 * * * *",
      "serviceAccountKey": { ... }
    },
    "default": {
      "useDefault": true,
      "selectAll": false,
      "monitoringRegions": ["us-central1", "us-east1"],
      "tags": [],
      "nameFilter": [],
      "deadOperation": "KEEP_7_DAYS",
      "disableTerminatedHostAlerting": true
    },
    "services": {
      "COMPUTEENGINE": { ... },
      "CLOUDSQL": { ... }
    }
  }
}
```

### 4.2 GCP Resource Manager API

#### 4.2.1 List Projects

```python
from google.cloud import resourcemanager_v3

client = resourcemanager_v3.ProjectsClient()

# List all projects accessible to the service account
request = resourcemanager_v3.SearchProjectsRequest(
    query="state:ACTIVE"
)

for project in client.search_projects(request=request):
    print(f"{project.project_id}: {project.display_name}")
```

---

## 5. Configuration

### 5.1 Configuration File (`config.yaml`)

```yaml
# LogicMonitor settings
logicmonitor:
  company: "your-company"
  auth_method: "bearer"  # or "lmv1"
  parent_group_id: 1
  
  # Credentials loaded from environment variables:
  # LM_BEARER_TOKEN or (LM_ACCESS_ID + LM_ACCESS_KEY)

# GCP settings
gcp:
  # Organization ID (optional - if not set, discovers all accessible projects)
  organization_id: null
  
  # Service account key path (or set GOOGLE_APPLICATION_CREDENTIALS)
  service_account_key_path: null
  
  # Project filters
  filters:
    include_patterns: []      # Glob patterns to include (empty = all)
    exclude_patterns:         # Glob patterns to exclude
      - "sys-*"
      - "*-sandbox"
    exclude_projects:         # Specific project IDs to exclude
      - "billing-export"
    
    # Only include projects with these labels
    required_labels: {}
    
    # Exclude projects with these labels
    excluded_labels:
      environment: "deprecated"

# Monitoring defaults
monitoring:
  netscan_frequency: "0 * * * *"
  dead_operation: "KEEP_7_DAYS"
  disable_terminated_alerting: true
  
  regions:
    - "us-central1"
    - "us-east1"
    - "us-west1"
    - "europe-west1"
    - "asia-east1"
  
  services:
    - "COMPUTEENGINE"
    - "CLOUDSQL"
    - "APPENGINE"
    - "CLOUDFUNCTIONS"
    - "GKE"
    - "CLOUDPUBSUB"
    - "CLOUDSTORAGE"
    - "CLOUDRUN"

# Sync behavior
sync:
  dry_run: false
  create_missing: true
  update_existing: false     # If true, updates config on existing integrations
  delete_removed: false      # If true, deletes LM groups for removed GCP projects
  
  # Naming template for LM groups
  group_name_template: "GCP - {project_id}"
  
  # Custom properties to add to all groups
  custom_properties:
    "lm.gcp.auto_managed": "true"
    "lm.gcp.managed_by": "lm-gcp-sync"

# Logging
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null  # Optional log file path
```

### 5.2 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LM_BEARER_TOKEN` | Yes* | LogicMonitor Bearer token |
| `LM_ACCESS_ID` | Yes* | LogicMonitor LMv1 Access ID |
| `LM_ACCESS_KEY` | Yes* | LogicMonitor LMv1 Access Key |
| `LM_COMPANY` | No | Override company from config |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to GCP service account key |
| `GCP_PROJECT_ID` | No | Default GCP project for API calls |

*Either `LM_BEARER_TOKEN` or both `LM_ACCESS_ID` and `LM_ACCESS_KEY` required.

---

## 6. Error Handling

### 6.1 Exception Hierarchy

```python
class LMGCPError(Exception):
    """Base exception for all lm-gcp-integration errors."""
    pass

class ConfigurationError(LMGCPError):
    """Configuration is invalid or missing."""
    pass

class AuthenticationError(LMGCPError):
    """Authentication failed."""
    pass

class LMAPIError(LMGCPError):
    """LogicMonitor API returned an error."""
    def __init__(self, message: str, status_code: int, response: dict):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class GCPAPIError(LMGCPError):
    """GCP API returned an error."""
    pass

class RateLimitError(LMAPIError):
    """Rate limit exceeded."""
    pass

class ProjectNotFoundError(LMGCPError):
    """GCP project not found."""
    pass

class GroupExistsError(LMGCPError):
    """LM group already exists for this project."""
    pass
```

### 6.2 Retry Strategy

```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "base_delay": 1.0,
    "max_delay": 30.0,
    "exponential_base": 2,
    "retryable_status_codes": [429, 500, 502, 503, 504],
}
```

---

## 7. Testing Strategy

### 7.1 Test Categories

| Category | Purpose | Tools |
|----------|---------|-------|
| Unit Tests | Test individual functions/methods | pytest, unittest.mock |
| Integration Tests | Test component interactions | pytest, responses/httpretty |
| E2E Tests | Test full workflow against real APIs | pytest (marked as slow) |

### 7.2 Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_config.py
│   ├── test_lm_client.py
│   ├── test_gcp_discovery.py
│   └── test_gcp_group_builder.py
├── integration/
│   ├── test_lm_api_integration.py
│   ├── test_gcp_api_integration.py
│   └── test_sync_workflow.py
└── e2e/
    └── test_full_sync.py
```

### 7.3 Mocking Strategy

- **LM API**: Use `responses` library to mock HTTP responses
- **GCP API**: Use `google-cloud-testutils` or mock client methods
- **Configuration**: Use pytest fixtures with temp files

---

## 8. Security Considerations

### 8.1 Credential Management

| Credential | Storage | Access |
|------------|---------|--------|
| LM Bearer Token | Environment variable | Runtime only |
| LM Access Key | Environment variable | Runtime only |
| GCP Service Account Key | File or Secret Manager | Read at startup |

### 8.2 Principle of Least Privilege

**GCP Service Account Permissions:**
- `roles/viewer` at organization level (read-only)
- `roles/resourcemanager.projectViewer` (alternative, more restrictive)

**LogicMonitor API User:**
- Manage permission on device groups
- No access to alerting, users, or other sensitive areas

### 8.3 Audit Logging

All sync operations logged with:
- Timestamp
- User/service account identity
- Action performed
- Projects affected
- Success/failure status

---

## 9. Deployment

### 9.1 Option 1: CLI Tool

```bash
# Install
pip install lm-gcp-integration

# Or from source
pip install -e .

# Run
export LM_BEARER_TOKEN="lmb_..."
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa-key.json"

lm-gcp-sync sync --config config.yaml
```

### 9.2 Option 2: Terraform

```bash
cd terraform/
terraform init
terraform plan -var-file="dev.tfvars"
terraform apply
```

### 9.3 Option 3: Cloud Function

```bash
cd cloud-function/
gcloud functions deploy lm-gcp-project-sync \
  --gen2 \
  --runtime python311 \
  --trigger-topic gcp-project-events \
  --set-secrets 'LM_BEARER_TOKEN=lm-credentials:latest'
```

---

## 10. Appendix

### 10.1 GCP Services Supported by LogicMonitor (Reference)

| Service ID | Display Name |
|------------|--------------|
| APPENGINE | App Engine |
| BIGQUERY | BigQuery |
| CLOUDAIPLATFORM | Cloud AI Platform |
| CLOUDAPIS | Cloud APIs |
| CLOUDBIGTABLE | Cloud Bigtable |
| CLOUDCOMPOSER | Cloud Composer |
| CLOUDDATAFLOW | Cloud Dataflow |
| CLOUDDATAPROC | Cloud Dataproc |
| CLOUDDLP | Cloud DLP |
| CLOUDDNS | Cloud DNS |
| CLOUDFILESTORE | Cloud Filestore |
| CLOUDFIRESTORE | Cloud Firestore |
| CLOUDFUNCTIONS | Cloud Functions |
| CLOUDINTERCONNECT | Cloud Interconnect |
| CLOUDIOT | Cloud IoT |
| CLOUDPUBSUB | Cloud Pub/Sub |
| CLOUDREDIS | Cloud Redis |
| CLOUDROUTER | Cloud Router |
| CLOUDRUN | Cloud Run |
| CLOUDSPANNER | Cloud Spanner |
| CLOUDSQL | Cloud SQL |
| CLOUDSTORAGE | Cloud Storage |
| CLOUDTASKS | Cloud Tasks |
| CLOUDTPU | Cloud TPU |
| CLOUDTRACE | Cloud Trace |
| COMPUTEENGINE | Compute Engine |
| COMPUTEENGINEAUTOSCALER | Compute Engine Autoscaler |
| GKE | Google Kubernetes Engine |
| HTTPLOADBALANCERS | HTTP(S) Load Balancers |
| NETWORKLOADBALANCERS | Network Load Balancers |
| MANAGEDSERVICEFORMICROSOFTAD | Managed Service for Microsoft AD |
| VPNGATEWAY | VPN Gateway |

### 10.2 GCP Regions

```yaml
regions:
  us:
    - us-central1
    - us-east1
    - us-east4
    - us-east5
    - us-south1
    - us-west1
    - us-west2
    - us-west3
    - us-west4
  europe:
    - europe-central2
    - europe-north1
    - europe-southwest1
    - europe-west1
    - europe-west2
    - europe-west3
    - europe-west4
    - europe-west6
    - europe-west8
    - europe-west9
  asia:
    - asia-east1
    - asia-east2
    - asia-northeast1
    - asia-northeast2
    - asia-northeast3
    - asia-south1
    - asia-south2
    - asia-southeast1
    - asia-southeast2
  other:
    - australia-southeast1
    - australia-southeast2
    - northamerica-northeast1
    - northamerica-northeast2
    - southamerica-east1
    - southamerica-west1
    - me-west1
    - me-central1
    - me-central2
    - africa-south1
```

### 10.3 References

- [LogicMonitor REST API - GCP Device Groups](https://www.logicmonitor.com/support/rest-api-developers-guide/v1/device-groups/gcp-device-groups)
- [Adding GCP Environment to LogicMonitor](https://www.logicmonitor.com/support/lm-cloud/getting-started-lm-cloud/adding-your-gcp-environment-into-logicmonitor)
- [GCP Resource Manager API](https://cloud.google.com/resource-manager/reference/rest)
- [Cloud Functions (2nd gen)](https://cloud.google.com/functions/docs/concepts/version-comparison)
