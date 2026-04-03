# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- AWS support with Organizations discovery (v2.1.0)
- Azure support with Management API discovery (v2.2.0)
- Multi-cloud sync feature (v3.0.0)

## [2.0.0] - 2025-01-XX

### Added
- Initial PyPI release
- GCP support with full provider implementation
  - Auto-discovery using Resource Manager API
  - Project-level integration management
  - Dry-run mode for safe testing
  - Orphan detection and cleanup
  - Status checking and sync operations
- CLI commands for GCP operations
  - `lm-cloud-sync gcp discover` - Discover GCP projects
  - `lm-cloud-sync gcp status` - Check sync status
  - `lm-cloud-sync gcp sync` - Sync projects to LogicMonitor
  - `lm-cloud-sync gcp delete` - Delete integrations
- Terraform module for GCP integrations
- Configuration management
  - YAML config file support
  - Environment variable overrides
  - Bearer token and LMv1 authentication
- Comprehensive documentation
  - Installation guide
  - Quick start guide
  - CLI usage examples
  - Publishing guide
  - Development setup

### Technical
- Python 3.11+ support
- Type hints throughout codebase
- Comprehensive test suite (81 tests)
- Linting with ruff
- Type checking with mypy
- Built with uv for fast dependency management

[unreleased]: https://github.com/ryanmat/lm-cloud-sync/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/ryanmat/lm-cloud-sync/releases/tag/v2.0.0
