# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-04-15

### Added
- Auth auto-detection: credentials determine auth method without explicit LM_AUTH_METHOD
- `--verbose` flag wires through to Python logging
- Lazy CLI imports so a broken GCP SDK no longer prevents AWS commands from loading
- Resync detects failed test results and sets status=warning
- GCP dry-run shows per-resource action list
- AWS status now shows full drift report
- Non-JSON error responses from the LM API handled gracefully

### Changed
- `--auto-discover` defaults to true for AWS and Azure providers
- GCP delete standardized to `--project-id` option
- `group_name_template` respected by all providers
- Azure SecretStr chain completed end-to-end
- ValidationError catch narrowed to ConfigurationError-relevant cases in config loading
- Bare except in sync narrowed to LMCloudSyncError

### Fixed
- Data envelope handling for LM API responses
- Exit codes: sync, resync, and delete now exit 1 on failure
- Masked fields warning no longer overwritten by subsequent error message
- Azure discovery bare except removed
- GCP unknown state log message corrected (was logging wrong state value)
- config.yaml added to .gitignore

### Removed
- Placeholder `all` command removed

## [2.1.0] - 2026-04-03

### Added
- AWS Organizations discovery via boto3
- AWS CLI commands (discover, sync, status, delete)
- Resync command: triggers LM sync engine via full PUT on cloud root groups
- Terraform AWS module with IAM hardening

### Fixed
- Silent failure on missing credentials during sync
- Credential values no longer logged in debug output

## [2.0.5] - 2026-03-15

### Added
- Azure subscription discovery via Management API
- Azure CLI commands (discover, sync, status, delete)
- Terraform Azure module

## [2.0.0] - 2026-01-15

### Added
- Initial release with GCP support
- Auto-discovery using Resource Manager API
- Project-level integration management
- Dry-run mode for safe testing
- Orphan detection and cleanup
- Status checking and sync operations
- CLI commands: `lm-cloud-sync gcp {discover,sync,status,delete}`
- Terraform module for GCP integrations
- YAML config file support with environment variable overrides
- Bearer token and LMv1 authentication
- Python 3.11+ support with full type hints

[3.0.0]: https://github.com/ryanmat/lm-cloud-sync/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/ryanmat/lm-cloud-sync/compare/v2.0.5...v2.1.0
[2.0.5]: https://github.com/ryanmat/lm-cloud-sync/compare/v2.0.0...v2.0.5
[2.0.0]: https://github.com/ryanmat/lm-cloud-sync/releases/tag/v2.0.0
