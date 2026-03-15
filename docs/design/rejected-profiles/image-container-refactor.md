# Proposal: Image and Execution Profile Refactor

> **Related work:** The [`skopeo` branch](https://github.com/datalad/datalad-container/tree/skopeo) implements OCI image storage via Skopeo. This proposal builds on that foundation.

## 1. Overview

This proposal refactors datalad-container to cleanly separate **image storage** from **execution configuration**. The result is a simpler, more flexible system where:

- Images are versioned artifacts with full provenance
- Execution profiles define how to run images, and can be shared/extended
- Provenance records the actual command that ran, not a shim

---

## 2. Current Problems

### 2.1 URL Scheme Conflates Multiple Concerns

The current URL scheme mixes source registry, storage format, and execution method:

```bash
docker://...        # Singularity pulls directly, stores as SIF
dhub://...          # Python adapter saves as tar, runs via shim
oci:docker://...    # Skopeo saves as OCI directory, runs via shim
shub://...          # Singularity Hub
```

Users must understand implementation details to choose the "right" URL scheme.

### 2.2 Execution Configuration is Inflexible

Execution is either:
- **Hardcoded in Python** - `docker_run()`, `podman_run()` with fixed flags
- **Baked in at add-time** - `cmdexec` set once, hard to change
- **Hidden from provenance** - shim invocation recorded, not actual command

Scientists need to run the same image differently:
- GPU vs CPU
- Different bind mounts
- Different runtimes (apptainer on HPC, podman on laptop)

### 2.3 Provenance Records Shims, Not Commands

Current run records show:
```
cmd: {python} -m datalad_container.adapters.oci run {img} {cmd}
```

This doesn't capture:
- Which runtime actually executed
- What flags were used

So we have reproducibility if everything "just works", but if anything goes wrong it is not possible to compare container runtime invocations.

### 2.4 Adding Runtimes Requires Code Changes

Supporting a new runtime (e.g., podman) requires:
- New Python functions (`podman_run()`)
- Runtime detection logic
- Testing across platforms

This doesn't scale and adds maintenance burden.

---

## 3. Proposed Design

### Summary

**Two concepts only:**

1. **Image** - versioned artifact with provenance, no execution semantics
2. **Execution Profile** (`profile`) - execution recipes that can be reused

**Key principles:**

- Protocol indicates registry source (`docker://`, `quay://`, `ghcr://`)
- Images stored in native OCI format, tracked by git-annex
- Profiles are YAML files that define `image` + `exec` template
- Profiles can extend other profiles (clobber semantics, no merging)
- CLI args (`--image`, `--exec`) override profile fields
- Provenance records the resolved command, not shim invocation

**File layout:**

```
.datalad/containers/
├── images/
│   └── mriqc/
│       ├── 23.1.0/
│       │   └── image/            # OCI directory
│       └── 24.0.0/
│           └── image/
└── profiles/
    ├── mriqc.yaml                # Base profile
    └── mriqc-gpu.yaml            # Extended profile
```

---

### 3.1 Image Storage Layer

#### Registry URL Scheme

Protocol indicates registry source only:

```bash
docker://org/repo:tag           # Docker Hub (docker.io)
quay://org/repo:tag             # Quay.io
ghcr://org/repo:tag             # GitHub Container Registry
shub://org/repo:tag             # Singularity Hub (legacy)
```

**Usage:**
```bash
datalad containers-add mriqc:23.1.0 --url docker://nipreps/mriqc:23.1.0
datalad containers-add samtools:1.9 --url quay://biocontainers/samtools:1.9
```

#### Storage Format

Images stored in their native format:

| Registry Type | Storage Format |
|---------------|----------------|
| Docker/OCI registries | OCI directory structure |
| Singularity Hub | SIF file |
| Local SIF file | Copy as-is |

OCI directory structure:
```
.datalad/containers/images/mriqc/23.1.0/
└── image/
    ├── blobs/sha256/...     # Layers (git-annex tracked)
    ├── index.json
    └── oci-layout
```

#### Git-annex Integration

Individual layers get registry URLs for efficient retrieval:
```bash
git annex whereis .datalad/containers/images/mriqc/23.1.0/image/blobs/sha256/abc123
# → docker.io/nipreps/mriqc@sha256:abc123
```

#### Provenance

Git commits capture provenance:
- Source URL
- Fetch timestamp
- Content checksums (via git-annex)

No separate provenance file needed - git is the provenance store.

#### Format Conversion (Optional)

Convert OCI to SIF for HPC performance:
```bash
datalad containers-convert mriqc/23.1.0 --to sif
# Creates: .datalad/containers/images/mriqc/23.1.0/image.sif
```

Both formats can coexist; profiles reference the appropriate one.

---

### 3.2 Execution Layer

#### Execution Profiles

Profiles are YAML files in `.datalad/containers/profiles/`:

```yaml
# .datalad/containers/profiles/alpine-docker.yaml
image: alpine:latest
exec: docker run --rm --user $(id -u):$(id -g) -v $(pwd):/work -w /work {img} {cmd}
```

```yaml
# .datalad/containers/profiles/alpine-apptainer.yaml
image: alpine:latest
exec: apptainer exec --cleanenv {img} {cmd}
```

#### Clobber Semantics

Child profiles **completely replace** parent values. No magic merging.

#### Cross-Dataset Extension

Profiles can extend profiles from subdatasets:

```yaml
# my-analysis/.datalad/containers/profiles/mriqc-local.yaml
extends: code/containers/.datalad/containers/profiles/mriqc.yaml
exec: apptainer exec --cleanenv --bind /scratch:/scratch {img} {cmd}
```

While this provides only minimal value like this, further development of to make profiles more
composable could make this very flexible and reusable.

```yaml
# my-analysis/.datalad/containers/profiles/mriqc-local.yaml
extends: code/containers/.datalad/containers/profiles/mriqc.yaml
binds: --bind /my/weird/scratch:/scratch
```

#### Placeholder Expansion

- `{img}` - Docker image name (`datalad-container/mriqc:23.1.0`)
- `{img_path}` - OCI directory path (`.datalad/containers/images/mriqc/23.1.0/image`)
- `{cmd}` - the command arguments

#### No Automatic Runtime Detection

Earlier designs considered inspecting `exec` to auto-detect runtime. **This is explicitly rejected.**

Each profile is explicit about its runtime:
- `mriqc-apptainer.yaml` - user writes `apptainer exec oci:{img_path} {cmd}`
- `mriqc-podman.yaml` - user writes `podman run {img} {cmd}`
- `mriqc-docker.yaml` - user writes `docker run --rm {img} {cmd}`

**Benefits:**
- No Python code per runtime
- Users control every flag
- Provenance records exactly what the user specified
- New runtimes require zero code changes

#### Provenance

Run records capture the **resolved command**:

```json
{
  "cmd": "apptainer exec --cleanenv --nv oci:.datalad/containers/images/mriqc/23.1.0/image mriqc /input /output participant",
  "profile": "mriqc-gpu",
  "profile-source": ".datalad/containers/profiles/mriqc-gpu.yaml"
}
```

The `cmd` is what actually ran. The profile reference is informational.

---

## 4. Interface Changes

### containers-add

```bash
# Add image from registry (name:version format, like Docker tags)
datalad containers-add mriqc:23.1.0 --url docker://nipreps/mriqc:23.1.0

# Add another version
datalad containers-add mriqc:24.0.0 --url docker://nipreps/mriqc:24.0.0

# Version defaults to URL tag if not specified
datalad containers-add alpine --url docker://alpine:3.18
# Creates alpine:3.18

# Override URL tag with explicit version
datalad containers-add alpine:prod --url docker://alpine:3.18
# Creates alpine:prod
```

After `containers-add`, the image is:
- Stored at `.datalad/containers/images/<name>/<version>/image/`
- Loaded into Docker daemon as `datalad-container/<name>:<version>`
- Ready to use: `docker run --rm datalad-container/mriqc:23.1.0 ...`

### containers-run

CLI args override profile fields. Precedence (highest to lowest):
1. CLI args (`--image`, `--exec`)
2. Profile fields
3. Extended profile fields (clobbered, not merged)

```bash
# Use profile as-is
datalad containers-run --profile mriqc <command>

# Override just exec (keep profile's image)
datalad containers-run --profile mriqc --exec "apptainer exec --nv {img} {cmd}" <command>

# Override just image (keep profile's exec)
datalad containers-run --profile mriqc --image mriqc:24.0.0 <command>

# Override both
datalad containers-run --profile mriqc --image mriqc:24.0.0 --exec "..." <command>

# No profile (must specify both)
datalad containers-run --image mriqc:23.1.0 --exec "apptainer exec {img} {cmd}" <command>
```

### New Commands

```bash
# List images
datalad containers-list

# List profiles
datalad containers-profiles

# Convert image format
datalad containers-convert <image-name> --to sif
```

---

## 5. Summary

| Aspect | Current | Proposed |
|--------|---------|----------|
| URL scheme | Mixed semantics | Protocol = registry |
| Storage format | Determined by URL | Native format from source |
| Provenance | Shim invocation | Actual command in git |
| Execution config | Baked in at add-time | Execution profiles |
| Profile reuse | Not possible | Profiles extend profiles |
| Runtime support | Requires code changes | Zero code changes |
| Configuration | .datalad/config (INI) | YAML files |

---

## 6. Implementation Plan

This work breaks into three phases that can be implemented and tested independently.

### Phase 1: Image Storage (builds on `skopeo` branch)

The `skopeo` branch already provides:
- OCI directory storage via Skopeo
- Git-annex tracking of layers
- Registry URL linking for efficient retrieval

**What's NOT done yet:**
- Clean URL scheme (`docker://` instead of `oci:docker://`)
- Support for `quay://`, `ghcr://` protocols
- Versioned image directories (`.datalad/containers/images/<name>/<version>/`)
- Remove `cmdexec` requirement from `containers-add`

**Milestone:** Images can be added and used with `datalad run` directly:

```bash
# Add image
datalad containers-add mriqc:23.1.0 --url docker://nipreps/mriqc:23.1.0

# Use with datalad run (no containers-run needed)
datalad run \
    --input .datalad/containers/images/mriqc/23.1.0 \
    --output outputs/ \
    "docker run --rm datalad-container/mriqc:23.1.0 mriqc ..."
```

This alone is valuable - full provenance, no shims, user controls execution.

---

### Phase 2: Recreate containers-run (no profiles)

Rebuild `containers-run` with explicit `--image` and `--exec` flags:

```bash
# With Docker
datalad containers-run \
    --image mriqc:23.1.0 \
    --exec "docker run --rm {img} {cmd}" \
    mriqc /data /output participant

# With Apptainer/Singularity
datalad containers-run \
    --image mriqc:23.1.0 \
    --exec "apptainer exec oci:{img_path} {cmd}" \
    mriqc /data /output participant
```

**Placeholders:**
- `{img}` - Docker image name (`datalad-container/mriqc:23.1.0`)
- `{img_path}` - OCI directory path (`.datalad/containers/images/mriqc/23.1.0/image`)
- `{cmd}` - command arguments

**What this provides:**
- `--image` specifies container name:version
- `--exec` is the execution template (required at this phase)
- Works with Docker, Apptainer, Singularity, Podman, etc.
- Provenance records the resolved command (not a shim)

**Milestone:** `containers-run` works without profiles, giving explicit control.

---

### Phase 3: Execution Profiles
**Status:** COMPLETE (2025-12-03)

Add YAML execution profile system on top of Phase 2:

```bash
# With profile
datalad containers-run --profile docker-default -- sh -c "echo hello"

# Override profile's exec
datalad containers-run --profile docker-default --exec "docker run --rm {img} {cmd}" ...

# Override profile's image
datalad containers-run --profile docker-default --image alpine:3.18 ...
```

**Implemented:**
- YAML profile files in `.datalad/containers/profiles/`
- Profile inheritance with clobber semantics via `extends:` key
- CLI overrides (`--image`, `--exec`) take precedence over profile
- `containers-profiles` command to list available profiles
- Early validation: error if profile references missing image
- pyyaml dependency added

**Tested:**
```bash
# docker-default.yaml: image: alpine:latest, exec: docker run --rm ... {img} {cmd}
datalad containers-run --profile docker-default -- sh -c "echo hello"

# apptainer-default.yaml: image: alpine:latest, exec: apptainer exec oci:{img_path} {cmd}
datalad containers-run --profile apptainer-default -- sh -c "echo hello"

# docker-myoverrides.yaml: extends: docker-default, exec: ... -e MY_VAR=hello {img} {cmd}
datalad containers-run --profile docker-myoverrides -- sh -c 'echo $MY_VAR'
# outputs: hello
```

**Value for ReproNim/containers:**
- Ship base profiles alongside images
- Users extend with their environment-specific settings
- Execution profiles are the "curated execution recipes" - ReproNim's value-add

**Milestone:** Full execution profile system, backward compatible with Phase 2 (can still use `--image` + `--exec` directly).

---

## 7. Breaking Changes (Phase 1)

Phase 1 introduces breaking changes to simplify the URL scheme and remove execution semantics from `containers-add`.

### URL Scheme Changes

| Old Scheme | New Behavior |
|------------|--------------|
| `docker://org/repo:tag` | **BREAKING**: Now stores as OCI directory via Skopeo (was: Singularity build to SIF) |
| `quay://org/repo:tag` | **NEW**: Stores as OCI directory via Skopeo |
| `ghcr://org/repo:tag` | **NEW**: Stores as OCI directory via Skopeo |
| `oci:docker://...` | **REMOVED**: Use `docker://` instead |
| `dhub://...` | **REMOVED**: Use `docker://` instead |
| `shub://...` | **REMOVED**: Singularity Hub deprecated |

**Migration path for `docker://` users who want SIF:**
```bash
# Old way (created SIF directly)
datalad containers-add myimg --url docker://org/repo:tag

# New way (OCI storage, convert to SIF separately)
datalad containers-add myimg --url docker://org/repo:tag
datalad containers-convert myimg --to sif  # Phase 1+ TODO
```

### Storage Path Changes

| Aspect | Old | New |
|--------|-----|-----|
| Default location | `.datalad/environments/<name>/image` | `.datalad/containers/images/<name>/<version>/image/` |
| Version in path | No | Yes (extracted from URL tag, defaults to `latest`) |
| Config storage | `.datalad/config` entries | Same (image path updated) |

### Execution Configuration Changes

| Aspect | Old | New (Phase 1) |
|--------|-----|---------------|
| `--call-fmt` parameter | Required or auto-guessed | **REMOVED** (commented out, TODO Phase 4) |
| `cmdexec` config | Set automatically | **NOT SET** |
| Auto-detection | Based on URL scheme | None - images have no execution semantics |

**Why this matters:** Phase 1 images are "just storage" - they don't know how to run. Users must specify execution explicitly via `datalad run` or wait for Phase 2's `--exec` flag.

---

## 8. Open Questions

1. **Custom registries** - How to specify private/custom OCI registries?

2. **Profile discovery** - How to list available profiles from subdatasets?

3. **Profile validation** - Warn if profile references unavailable image or runtime?

4. **Placeholder expansion** - What placeholders beyond `{img}` and `{cmd}`? (`{pwd}`, `{uid}`?)

5. **Image format conversion** - On-demand or explicit `containers-convert` command?

6. **Backward compatibility** - How to handle existing datasets using old format?

   Current format stores in `.datalad/config`:
   ```ini
   datalad.containers.mriqc.image = .datalad/environments/mriqc/image
   datalad.containers.mriqc.cmdexec = {python} -m datalad_container.adapters.oci run {img} {cmd}
   ```

   Issues to resolve:
   - **`-n` flag**: Keep as alias for `--profile`? Or separate lookup for old vs new?
   - **Image paths**: Old `.datalad/environments/<name>/image` vs new `.datalad/containers/images/<name>/<version>/image`
   - **No version in old naming**: Old `mriqc` vs new `mriqc/23.1.0` - use `latest` as default version?
   - **Shim cmdexec**: Old shims still work but defeat provenance goals

   Possible approaches:

   **A. `containers-migrate` command:**
   - Move images: `.datalad/environments/<name>/` → `.datalad/containers/images/<name>/latest/`
   - Generate profile from old cmdexec
   - Remove old config entries
   - Optionally prompt user to simplify shim exec to direct invocation

   **B. Dual lookup (no migration required):**
   - `-n` checks new profiles first, falls back to old config
   - Old datasets keep working without changes
   - New features only available after migration

   **C. Deprecation without migration:**
   - Old format works but emits warnings
   - Document manual migration steps
   - Eventually remove old code paths
