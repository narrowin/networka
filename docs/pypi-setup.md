# PyPI Publishing Setup

This document describes how to configure PyPI publishing for the networka project.

## GitHub Repository Configuration

### 1. Set up PyPI Trusted Publishing

1. Go to [PyPI](https://pypi.org) and create an account if needed
2. Create a new project called `networka`
3. Go to "Publishing" → "Add a new pending publisher"
4. Fill in:
   - **PyPI Project Name**: `networka`
   - **Owner**: `narrowin`
   - **Repository name**: `networka`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`

### 2. Set up TestPyPI Trusted Publishing

1. Go to [TestPyPI](https://test.pypi.org) and create an account
2. Create a new project called `networka`
3. Go to "Publishing" → "Add a new pending publisher"
4. Fill in:
   - **PyPI Project Name**: `networka`
   - **Owner**: `narrowin`
   - **Repository name**: `networka`
   - **Workflow name**: `release.yml`
   - **Environment name**: `testpypi`

### 3. Configure GitHub Environments

1. Go to GitHub repository Settings → Environments
2. Create environment `pypi`:
   - No deployment protection rules needed (trusted publishing handles authentication)
3. Create environment `testpypi`:
   - No deployment protection rules needed

## Local Publishing Setup (Optional)

For manual publishing using `task publish:test` or `task publish:pypi`:

### 1. Configure PyPI credentials

```bash
# Create pypirc file
mkdir -p ~/.pypirc

# Edit ~/.pypirc
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <your-pypi-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-testpypi-token>
```

### 2. Generate API tokens

1. PyPI: Go to Account Settings → API tokens → "Add API token"
2. TestPyPI: Go to Account Settings → API tokens → "Add API token"
3. Use project-scoped tokens when available

## Publishing Process

### Automated (Recommended)

1. Create a release using the release script:

   ```bash
   ./scripts/release.sh --version 1.0.0
   ```

2. GitHub Actions will automatically:
   - Build the package
   - Test installation on multiple platforms
   - Create GitHub release
   - Publish to PyPI (stable) or TestPyPI (pre-release)

### Manual (Local)

```bash
# Test on TestPyPI first
task publish:test

# If successful, publish to PyPI
task publish:pypi
```

## Release Types

- **Stable releases** (e.g., `1.0.0`): Published to PyPI
- **Pre-releases** (e.g., `1.0.0-rc1`, `1.0.0a1`): Published to TestPyPI

## Troubleshooting

### Common Issues

1. **Version already exists**: PyPI doesn't allow overwriting. Bump version and try again.
2. **Authentication failed**: Check API tokens and trusted publishing configuration.
3. **Package validation failed**: Run `uv run twine check dist/*` to identify issues.

### Testing Installation

```bash
# Test from TestPyPI
pip install --index-url https://test.pypi.org/simple/ networka

# Test from PyPI
pip install networka
```
