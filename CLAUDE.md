# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

datalad-container is a DataLad extension for working with containerized computational environments. It enables tracking, versioning, and execution of containerized workflows within DataLad datasets using Singularity/Apptainer, Docker, and OCI-compliant images.

## Core Architecture

### Command Suite Structure

The extension registers a command suite with DataLad through setuptools entry points (see `setup.cfg`). The main commands are:

- **containers-add** (`containers_add.py`) - Add/update container images to a dataset
- **containers-list** (`containers_list.py`) - List configured containers
- **containers-remove** (`containers_remove.py`) - Remove containers from configuration
- **containers-run** (`containers_run.py`) - Execute commands within containers

All commands are registered in `datalad_container/__init__.py` via the `command_suite` tuple.

### Container Adapters

The `adapters/` directory contains transport-specific handlers:

- **docker.py** - Docker Hub images (`dhub://` scheme)
- **oci.py** - OCI-compliant images using Skopeo (`oci:` scheme)
  - Saves images as trackable directory structures
  - Supports loading images to Docker daemon on-demand
  - Uses Skopeo for image manipulation

Each adapter implements `save()` and `run()` functions for their respective container formats.

### Container Discovery

`find_container.py` implements the logic for locating containers:
- Searches current dataset and subdatasets
- Supports hierarchical container names (e.g., `subds/container-name`)
- Falls back to path-based and name-based lookups
- Automatically installs subdatasets if needed to access containers

### Configuration Storage

Container metadata is stored in `.datalad/config` with the pattern:
```
datalad.containers.<name>.image = <relative-path>
datalad.containers.<name>.cmdexec = <execution-format-string>
datalad.containers.<name>.updateurl = <original-url>
datalad.containers.<name>.extra-input = <additional-dependencies>
```

Default container location: `.datalad/environments/<name>/image`

## Development Commands

### Setup Development Environment

```bash
# Using uv (preferred)
uv venv
source .venv/bin/activate
uv pip install -e .[devel]

# Or traditional method
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[devel]
```

### Running Tests

```bash
# Run all tests
pytest -s -v datalad_container

# Run specific test file
pytest -s -v datalad_container/tests/test_containers.py

# Run specific test function
pytest -s -v datalad_container/tests/test_containers.py::test_add_noop

# Run with coverage
pytest -s -v --cov=datalad_container datalad_container

# Skip slow tests (marked with 'turtle')
pytest -s -v -m "not turtle" datalad_container
```

### Code Quality Tools

Pre-commit hooks are configured in `.pre-commit-config.yaml`:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Individual tools
isort datalad_container/  # Sort imports
codespell                  # Spell checking
```

### Building Documentation

```bash
cd docs
make html
# Output in docs/build/html/
```

### Important Testing Notes

- Tests use pytest fixtures defined in `datalad_container/conftest.py` and `tests/fixtures/`
- The project uses `@with_tempfile` and `@with_tree` decorators from DataLad's test utilities
- Docker tests may require Docker to be running
- Singularity/Apptainer tests require the container runtime to be installed
- Some tests are marked with `@pytest.mark.turtle` for slow-running tests

## Key Implementation Details

### URL Scheme Handling

Container sources are identified by URL schemes:
- `shub://` - Singularity Hub (legacy, uses requests library)
- `docker://` - Direct Singularity pull from Docker Hub
- `dhub://` - Docker images stored locally via docker pull/save
- `oci:` - OCI images stored as directories via Skopeo

The scheme determines both storage format and execution template.

### Execution Format Strings

Call format strings support placeholders:
- `{img}` - Path to container image
- `{cmd}` - Command to execute
- `{img_dspath}` - Relative path to dataset containing image
- `{img_dirpath}` - Directory containing the image
- `{python}` - Path to current Python executable

Example: `singularity exec {img} {cmd}`

### Git-annex Integration

- Large container images are managed by git-annex
- For `shub://` URLs, uses DataLad's special remote if available
- The `ensure_datalad_remote()` function (in `utils.py`) initializes the special remote when needed
- For `oci:docker://` images, registry URLs are added to annexed layers for efficient retrieval

### Path Normalization

`utils.py` contains `_normalize_image_path()` to handle cross-platform path issues:
- Config historically stored platform-specific paths
- Now standardizes to POSIX paths in config
- Maintains backward compatibility with Windows paths

## Testing Considerations

- Mark AI-generated tests with `@pytest.mark.ai_generated`
- Tests should not `chdir()` the entire process; use `cwd` parameter instead
- Use `common_kwargs = {'result_renderer': 'disabled'}` in tests to suppress output
- Many tests use DataLad's `with_tempfile` decorator for temporary test directories

## Dependencies

Core dependencies:
- datalad >= 0.18.0
- requests >= 1.2 (for Singularity Hub communication)

Container runtimes (at least one required):
- Singularity or Apptainer for Singularity images
- Docker for Docker and OCI image execution
- Skopeo for OCI image manipulation

## Version Management

This project uses `versioneer.py` for automatic version management from git tags. Version info is in `datalad_container/_version.py` (auto-generated, excluded from coverage).
