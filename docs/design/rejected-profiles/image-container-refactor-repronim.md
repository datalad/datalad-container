# ReproNim/containers Integration with Refactored datalad-container

This document describes how ReproNim/containers can leverage the refactored datalad-container architecture.

STATUS: Very rough draft! 

---

## New Capabilities

### 1. Multiple Image Formats and Versions

With native format storage and versioned image directories, ReproNim can provide:

**Multiple versions per image:**
```
.datalad/containers/images/
├── mriqc/
│   ├── 23.1.0/
│   │   ├── image/          # OCI directory
│   │   └── image.sif       # Optional SIF
│   └── 24.0.0/
│       └── image/
└── fmriprep/
    ├── 23.2.0/
    │   └── image/
    └── 24.1.0/
        └── image/
```

**Image naming:** Use `name:version` format (like Docker tags):
- `mriqc:23.1.0` → `.datalad/containers/images/mriqc/23.1.0/image/`
- `fmriprep:24.1.0` → `.datalad/containers/images/fmriprep/24.1.0/image/`

### Benefits of OCI format for ReproNim:

- **Layer deduplication** - Many neuroimaging containers share base layers
- **Incremental updates** - Only changed layers need to be fetched
- **Registry retrieval** - git-annex can fetch layers directly from Docker Hub
- **Multi-runtime** - Works with apptainer, podman, docker without conversion

---

## 2. Execution Profiles

ReproNim can ship curated execution profiles alongside images. Users extend these for their specific needs.

### Available Placeholders

- `{img}` - Docker image name (`datalad-container/mriqc:23.1.0`)
- `{img_path}` - OCI directory path (`.datalad/containers/images/mriqc/23.1.0/image`)
- `{cmd}` - command arguments

### ReproNim Base Profiles

**Option A: Profiles with image (ready to use)**

```yaml
# .datalad/containers/profiles/mriqc.yaml
# Base MRIQC profile - sane defaults for most users

image: mriqc:23.1.0
exec: apptainer exec --cleanenv oci:{img_path} {cmd}
```

```yaml
# .datalad/containers/profiles/fmriprep.yaml
# Base fMRIPrep profile

image: fmriprep:23.2.0
exec: apptainer exec --cleanenv oci:{img_path} {cmd}
```

**Option B: Runtime-only profiles (user specifies image)**

```yaml
# .datalad/containers/profiles/apptainer-default.yaml
# No image - user must provide --image

exec: apptainer exec oci:{img_path} {cmd}
```

```yaml
# .datalad/containers/profiles/docker-default.yaml

exec: docker run --rm --user $(id -u):$(id -g) -v $(pwd):/work -w /work {img} {cmd}
```

Usage: `datalad containers-run --profile apptainer-default --image mriqc:23.1.0 ...`

### User Extensions

Users create their own profiles that extend ReproNim's base:

```yaml
# my-analysis/.datalad/containers/profiles/mriqc-mylab.yaml

extends: inputs/containers/.datalad/containers/profiles/mriqc.yaml
exec: apptainer exec --cleanenv --nv --bind /scratch:/scratch --bind /data/mylab:/input oci:{img_path} {cmd}
```

```yaml
# my-analysis/.datalad/containers/profiles/mriqc-gpu.yaml

extends: inputs/containers/.datalad/containers/profiles/mriqc.yaml
exec: apptainer exec --cleanenv --nv oci:{img_path} {cmd}
```

**Key point:** ReproNim provides the base. Users clobber `exec` with their environment-specific settings (clobber semantics - child completely replaces parent's exec, no merging).

---

## 3. Dataset Structure

### Proposed ReproNim/containers layout:

```
ReproNim/containers/
├── .datalad/containers/
│   ├── images/
│   │   ├── mriqc/
│   │   │   ├── 23.1.0/
│   │   │   │   ├── image/
│   │   │   │   └── image.sif
│   │   │   └── 24.0.0/
│   │   │       └── image/
│   │   └── fmriprep/
│   │       ├── 23.2.0/
│   │       │   └── image/
│   │       └── 24.1.0/
│   │           └── image/
│   └── profiles/
│       ├── mriqc.yaml
│       ├── mriqc-24.yaml
│       ├── fmriprep.yaml
│       └── fmriprep-24.yaml
│
├── binds/
│   ├── HOME/                    # Fake home with .bashrc, .gitconfig
│   └── zoneinfo/UTC             # Timezone file
│
├── scripts/
│   ├── setup-env.sh             # Pre-run hook for profiles
│   ├── cleanup.sh               # Post-run hook for profiles
│   └── freeze_versions          # Version pinning tool
│
└── README.md
```

Provenance (source URL, digest, fetch time) is stored in git commits, not separate files.

---

## 4. Workflow Examples

### Basic Usage

```bash
# Get ReproNim containers
datalad clone https://github.com/ReproNim/containers inputs/containers

# List available images and profiles
datalad containers-list -d inputs/containers
datalad containers-profiles -d inputs/containers

# Run with base profile (profile specifies image)
datalad containers-run --profile mriqc -- mriqc /bids /outputs participant

# Or use runtime-only profile with explicit image
datalad containers-run --profile apptainer-default --image mriqc:23.1.0 -- mriqc /bids /outputs participant
```

### Creating a Lab-Specific Profile

```bash
# Create your own profile extending ReproNim's base
mkdir -p .datalad/containers/profiles
cat > .datalad/containers/profiles/mriqc-mylab.yaml << 'EOF'
extends: inputs/containers/.datalad/containers/profiles/mriqc.yaml
exec: apptainer exec --cleanenv --nv --bind /scratch:/scratch --bind /gpfs/mylab:/data oci:{img_path} {cmd}
EOF

# Save to dataset
datalad save -m "Add mriqc-mylab profile" .datalad/containers/profiles/

# Use it
datalad containers-run --profile mriqc-mylab -- mriqc /data/bids /data/outputs participant
```

### One-Off Override

```bash
# Use base profile but override exec for this run (adds GPU support)
datalad containers-run --profile mriqc \
    --exec "apptainer exec --cleanenv --nv oci:{img_path} {cmd}" \
    -- mriqc /bids /outputs participant

# Use base profile but override image (use newer version)
datalad containers-run --profile mriqc --image mriqc:24.0.0 \
    -- mriqc /bids /outputs participant
```

### Using a Specific Version

```bash
# Create profile for newer version
cat > .datalad/containers/profiles/mriqc-24.yaml << 'EOF'
image: mriqc:24.0.0
exec: apptainer exec --cleanenv oci:{img_path} {cmd}
EOF

datalad save -m "Add mriqc-24 profile" .datalad/containers/profiles/
datalad containers-run --profile mriqc-24 -- mriqc /bids /outputs participant
```

---

## 5. Migration Path

### Phase 1: Add new structure (non-breaking)

- Add `.datalad/containers/images/` with versioned directories
- Add `.datalad/containers/profiles/` YAML files
- Add OCI images alongside existing SIF files
- Keep existing `.datalad/config` entries

### Phase 2: Recommend new approach

- Default documentation uses profiles
- Legacy config still works
- Add migration guide

### Phase 3: Simplify storage

- Consider generating SIF on-demand with `containers-convert`
- Or keep both for user convenience

---

## 6. Benefits Summary

| Aspect | Current | With Refactor |
|--------|---------|---------------|
| Image formats | SIF only | SIF + OCI |
| Image versions | Flat naming | Structured versioning |
| Layer sharing | None | Deduplication across containers |
| Execution config | Hardcoded in wrapper | Base profiles, user-extendable |
| Runtime flexibility | Singularity only | Any runtime via profile |
| Provenance | Wrapper invocation | Actual command recorded |
| Customization | Fork or edit wrapper | Extend profile, clobber exec |
| HPC adaptation | Manual | User creates their own profile |

---

## 7. Replacing singularity_cmd with Profiles

The current `singularity_cmd` shim provides many features. With profile extensions, most can be handled declaratively.

### Current shim features

| Feature | Description |
|---------|-------------|
| Fake HOME | Custom home with minimal .bashrc/.gitconfig |
| Git config passthrough | Copies user.name, user.email, annex.pidlock, safe.directory |
| Isolated /tmp | Creates temp dir, binds as /tmp and /var/tmp, cleans up |
| Environment sanitization | `--cleanenv`, `--contain` flags |
| DATALAD_CONTAINER_NAME | Exports via SINGULARITYENV_*/APPTAINERENV_* |
| Timezone handling | Binds zoneinfo/UTC to /etc/localtime |
| Matplotlib fix | Sets MPLCONFIGDIR=/tmp/mpl-config |
| Docker fallback | Runs singularity inside Docker on non-Linux |
| Duct integration | Optional resource monitoring wrapper |

### What profiles can handle today

Static flags work directly in `exec`:

```yaml
exec: >-
  apptainer exec
  --cleanenv
  --contain
  -H code/containers/binds/HOME
  -B code/containers/binds/zoneinfo/UTC:/etc/localtime
  oci:{img_path}
  {cmd}
```

**Available placeholders:**
- `{img}` - Docker image name (for docker/podman)
- `{img_path}` - OCI directory path (for apptainer with `oci:` prefix)
- `{cmd}` - command arguments

### Upstream RFE: Advanced Profile Features

To fully replace the shim, datalad-container would need these profile extensions:

#### 1. `env` section - static environment variables

```yaml
env:
  SINGULARITYENV_MPLCONFIGDIR: /tmp/mpl-config
  APPTAINERENV_MPLCONFIGDIR: /tmp/mpl-config
```

#### 2. `pre-run` hook - script executed before container

```yaml
pre-run: code/containers/scripts/setup-env.sh
```

The script would:
- Create temp directory, export as `TMPDIR`
- Generate .gitconfig from current git config
- Export `SINGULARITYENV_DATALAD_CONTAINER_NAME`

#### 3. `post-run` hook - script executed after container

```yaml
post-run: code/containers/scripts/cleanup.sh
```

The script would:
- Remove temp directory

#### 4. `{env.VARNAME}` placeholder - reference env vars in exec

```yaml
exec: >-
  apptainer exec
  -B {env.TMPDIR}:/tmp
  -H {env.BHOME}
  {img}
  {cmd}
```

### Full profile replacing singularity_cmd

With these extensions, a profile could fully replace the shim:

```yaml
# .datalad/containers/profiles/mriqc-repronim.yaml

image: mriqc:23.1.0

pre-run: code/containers/scripts/setup-env.sh
post-run: code/containers/scripts/cleanup.sh

env:
  SINGULARITYENV_MPLCONFIGDIR: /tmp/mpl-config
  APPTAINERENV_MPLCONFIGDIR: /tmp/mpl-config

exec: >-
  apptainer exec
  --cleanenv
  --contain
  -H {env.BHOME}
  -B {env.TMPDIR}:/tmp
  -B {env.TMPDIR}/var:/var/tmp
  -B code/containers/binds/zoneinfo/UTC:/etc/localtime
  oci:{img_path}
  {cmd}
```

### Docker fallback as separate profile

Instead of runtime detection, use a separate profile:

```yaml
# .datalad/containers/profiles/mriqc-repronim-docker.yaml
# For non-Linux systems (macOS, Windows with Docker)

image: mriqc:23.1.0

pre-run: code/containers/scripts/setup-env-docker.sh

env:
  MPLCONFIGDIR: /tmp/mpl-config

exec: >-
  docker run
  --rm
  --user $(id -u):$(id -g)
  -v $(pwd):/work
  -w /work
  {img}
  {cmd}
```

Users on macOS would use `--profile mriqc-repronim-docker` explicitly.

**Note:** The Docker profile uses `{img}` (the Docker image name like `datalad-container/mriqc:23.1.0`) while apptainer profiles use `{img_path}` (the OCI directory path).

### Summary: Upstream RFE for datalad-container

To enable ReproNim to replace `singularity_cmd` with profiles:

1. **`env:` section** - Static environment variable definitions
2. **`pre-run:` hook** - Script to run before exec (can export env vars)
3. **`post-run:` hook** - Script to run after exec (cleanup)
4. **`{env.VARNAME}` placeholder** - Reference environment variables in exec template

These are optional extensions - basic profiles work without them.

---

## 8. Open Questions for ReproNim

1. **Dual format storage** - Ship both OCI and SIF, or OCI-only with on-demand conversion?

2. **Base profile scope** - Just image + minimal exec, or include ReproNim sanitization defaults?

3. **Profile per version** - One profile per version (mriqc-23.yaml, mriqc-24.yaml) or update profile to point to latest?

4. **Backward compatibility** - How long to maintain legacy `.datalad/config` entries and `singularity_cmd`?

5. **Docker fallback** - Separate profile (explicit) or some detection mechanism?

6. **Duct integration** - Wrapper in pre-run, or dedicated profile field?
