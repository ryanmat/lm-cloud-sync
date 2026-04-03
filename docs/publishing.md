# Publishing to PyPI

This guide covers the process for publishing new versions of lm-cloud-sync to PyPI.

## Prerequisites

1. PyPI account (create at https://pypi.org/account/register/)
2. PyPI API token (create at https://pypi.org/manage/account/token/)
3. UV installed locally

## Setup (One-time)

### Store PyPI Credentials

```bash
# Set your PyPI token
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"

# Or store in ~/.pypirc
cat > ~/.pypirc <<EOF
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
EOF
```

## Publishing Process

### 1. Update Version

Edit `pyproject.toml`:

```toml
[project]
version = "2.1.0"  # Increment according to semver
```

### 2. Update CHANGELOG

Add release notes to `CHANGELOG.md`:

```markdown
## [2.1.0] - 2025-XX-XX

### Added
- AWS support with Organizations discovery
- New `aws` CLI commands

### Fixed
- Bug fixes and improvements
```

### 3. Commit Version Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 2.1.0"
git push origin main
```

### 4. Build Package

```bash
# Clean previous builds
rm -rf dist/

# Build the package
uv build

# This creates:
# - dist/lm_cloud_sync-2.1.0-py3-none-any.whl
# - dist/lm_cloud_sync-2.1.0.tar.gz
```

### 5. Test Build Locally

```bash
# Install in a fresh environment
uv venv test-env
source test-env/bin/activate
uv pip install dist/lm_cloud_sync-2.1.0-py3-none-any.whl

# Test it works
lm-cloud-sync --version
lm-cloud-sync --help

# Clean up
deactivate
rm -rf test-env
```

### 6. Publish to PyPI

```bash
# Publish to PyPI
uv publish

# Or publish with explicit token
uv publish --token $UV_PUBLISH_TOKEN
```

### 7. Create Git Tag

```bash
# Tag the release
git tag -a v2.1.0 -m "Release v2.1.0: AWS support"
git push origin v2.1.0
```

### 8. Create GitHub Release

1. Go to https://github.com/ryanmat/lm-cloud-sync/releases/new
2. Select tag: `v2.1.0`
3. Title: `v2.1.0: AWS Support`
4. Description: Copy from CHANGELOG.md
5. Attach build artifacts (optional)
6. Publish release

### 9. Verify Installation

```bash
# Test installation from PyPI
pip install lm-cloud-sync==2.1.0

# Or upgrade
pip install --upgrade lm-cloud-sync
```

## Versioning Strategy

Follow semantic versioning (semver):

- **Major** (3.0.0): Breaking changes, major new features
- **Minor** (2.1.0): New features, backward compatible
- **Patch** (2.0.1): Bug fixes, backward compatible

### Current Plan

- **v2.0.0**: GCP support (initial PyPI release)
- **v2.1.0**: Add AWS support
- **v2.2.0**: Add Azure support
- **v3.0.0**: Multi-cloud sync feature

## Troubleshooting

### Package name already taken

If `lm-cloud-sync` is taken on PyPI:

```toml
# In pyproject.toml
name = "logicmonitor-cloud-sync"  # Or another variant
```

### Build fails

```bash
# Check for issues
uv run ruff check src/
uv run mypy src/
uv run pytest

# Fix issues before building
```

### Publish fails with 403

- Check your API token is valid
- Ensure you have permissions for the package name
- For first publish, you need to own the package name

## Best Practices

1. Always test the build locally before publishing
2. Keep CHANGELOG.md updated with each release
3. Tag releases in git for version tracking
4. Create GitHub releases for visibility
5. Never delete published versions (PyPI doesn't allow it)
6. If you need to fix a published version, publish a patch (e.g., 2.0.1)

## Automation (Future)

Consider setting up GitHub Actions to automate publishing:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv build
      - run: uv publish --token ${{ secrets.PYPI_TOKEN }}
```

## Support

- PyPI docs: https://packaging.python.org/
- UV docs: https://docs.astral.sh/uv/
- Semantic versioning: https://semver.org/
