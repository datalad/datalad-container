# OCI Storage Refactor

This document describes changes to datalad-container's image storage and URL handling.

Builds on the skopeo OCI image storage PR: https://github.com/datalad/datalad-container/pull/277/

## Goals

1. **Support multiple runtimes** - Docker, Podman, Apptainer, Singularity should all work
2. **Don't reinvent the wheel** - Use existing patterns (cmdexec, shims) rather than new abstractions
3. **More intuitive configuration** - Current configuration path requires too much knowledge of internals; should feel natural to users familiar with containers
4. **Consistent with container conventions** - Follow OCI/Docker naming/tagging conventions users already know
5. **Preserve backwards compatibility** - Existing datasets and workflows continue to work
6. **Remain HPC-friendly** - Continue to work well on HPC systems (Apptainer/Singularity, no root)

### Non-Goals

- Runtime auto-detection (users specify what they want)
- Replacing cmdexec with a new execution system
- Breaking existing container configurations
- Improving reproducibility (already good, don't regress)

### Currently missing: Multiple container runtimes, user choice

   - Currently: the runtime is automatically determined by the --url with confusing "protocols" ie `oci:docker://`
   - To change, users have to write their own cmdexec string, understand placeholder syntax
   - Should be: Simple flag or obvious configuration

## Summary

- `docker://` URLs store images as OCI directories via Skopeo (not singularity build)
- Image paths include version: `.datalad/environments/<name>/<version>/image/`
    - (allows names to match upstream repository)
- New `--runtime` flag on `containers-add` to select docker/podman/apptainer
- New `runtime` configuration option in `.datalad/config`

## Proposed Changes

### 1. docker:// Uses OCI Storage

**Before:** `docker://` triggered `singularity build`, creating a SIF file.

**After:** `docker://` uses Skopeo to save as OCI directory structure.

```bash
datalad containers-add alpine --url docker://alpine:3.18
# Creates: .datalad/environments/alpine/3.18/image/ (OCI directory)
```

Benefits:
- Layer deduplication via git-annex
- Registry URLs linked to layers for efficient retrieval
- Works with docker/podman natively, apptainer via `oci:` prefix

### 2. Versioned Storage Paths

Versions can be tags or shas.

**Before:** `.datalad/environments/<name>/image`

**After:** `.datalad/environments/<name>/<version>/image/`

Version is extracted from URL:
- `docker://alpine:3.18` → version `3.18`
- `docker://nipreps/mriqc:23.1.0` → version `23.1.0`
- `docker://alpine` → version `latest`
- `docker://alpine@sha256:abc123` → version `sha256_abc123`

### 3. Execution via OCI Shim

Images are executed via the OCI adapter shim:

```ini
# .datalad/config
[datalad "containers.alpine"]
    image = .datalad/environments/alpine/3.18/image
    cmdexec = {python} -m datalad_container.adapters.oci run {img} {cmd}
```

The shim:
1. Loads OCI directory into container runtime (docker/podman)
2. Runs container with appropriate flags
3. Works transparently with `datalad containers-run`

### 4. Runtime Selection via `--runtime` Flag

Add `--runtime` flag to `containers-add` for choosing execution runtime:

```bash
datalad containers-add alpine --url docker://alpine:3.18 --runtime docker   # default
datalad containers-add alpine --url docker://alpine:3.18 --runtime podman
datalad containers-add alpine --url docker://alpine:3.18 --runtime apptainer
```

**Behavior:**
- Stores runtime preference in config: `datalad.containers.<name>.runtime`
- OCI shim reads this config and executes with the appropriate runtime
- If `--runtime apptainer`: also converts OCI → SIF at add-time

**Config examples:**

Docker/Podman (uses OCI shim):
```ini
[datalad "containers.alpine"]
    image = .datalad/environments/alpine/3.18/image
    cmdexec = {python} -m datalad_container.adapters.oci run {img} {cmd}
    runtime = docker
```

Apptainer (converts to SIF, uses singularity exec directly):
```ini
[datalad "containers.alpine"]
    image = .datalad/environments/alpine/3.18/image.sif
    cmdexec = singularity exec {img} {cmd}
```

### 5. Deprecate dhub://

`dhub://` uses docker pull + docker save (tar format).
`docker://` now uses skopeo + OCI directory (better for git-annex).

Options:
- Deprecate with warning
- Remove entirely
- Make alias to docker://

## URL Scheme Summary

| Scheme | Storage Format | Execution |
|--------|---------------|-----------|
| `docker://` | OCI directory | OCI shim (docker/podman) or apptainer |
| `shub://` | SIF file | singularity exec |

**Removed/Deprecated:**
- `oci:docker://` - redundant, `docker://` now uses OCI storage
- `dhub://` - deprecated, use `docker://` instead

## Backward Compatibility

- Old containers (without version in path) continue to work
- `cmdexec` shim pattern preserved
- No changes to `containers-run` interface
