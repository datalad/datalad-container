# Tutorial: MRIQC Quality Control with datalad-container

This tutorial demonstrates using datalad-container to download a container image directly, create an execution profile from scratch, and run a containerized analysis.

---

## Prerequisites

```bash
# Install datalad and extensions
pip install datalad datalad-container

# Install container tools
sudo apt-get install apptainer skopeo
```

---

## Step 1: Create Your Analysis Dataset

```bash
datalad create -c text2git mriqc-analysis
cd mriqc-analysis
```

---

## Step 2: Add the MRIQC Container Image

Download the container image directly from Docker Hub:

```bash
# Add the MRIQC image (OCI format)
datalad containers-add mriqc/23.1.0 --url docker://nipreps/mriqc:23.1.0

# Verify the image was added
ls .datalad/containers/images/mriqc/23.1.0/
# image/  (OCI directory structure)

# Provenance is in the git commit
git log --oneline -1
# abc123 Add container image mriqc/23.1.0 from docker://nipreps/mriqc:23.1.0
```

---

## Step 3: Create an Execution Profile

Profiles define HOW to run the image. Create one for your environment:

```bash
mkdir -p .datalad/containers/profiles

cat > .datalad/containers/profiles/mriqc.yaml << 'EOF'
# Basic MRIQC execution profile
image: mriqc/23.1.0

exec: >-
  apptainer exec
  --cleanenv
  {img}
  {cmd}
EOF

datalad save -m "Add MRIQC image and profile"
```

**What the placeholders mean:**
- `{img}` - Resolves to `oci:.datalad/containers/images/mriqc/23.1.0/image`
- `{cmd}` - Replaced with your command arguments

---

## Step 4: Install Input Data

```bash
# Install a demo BIDS dataset
datalad install -d . -s https://github.com/ReproNim/ds000003-demo sourcedata/raw

# Ignore working directory
echo "workdir/" >> .gitignore
datalad save -m "Add input data, ignore workdir"
```

---

## Step 5: Run MRIQC

```bash
datalad containers-run \
    --profile mriqc \
    --input sourcedata/raw \
    --output . \
    mriqc sourcedata/raw outputs participant --participant-label 01
```

**What happens:**
1. Profile `mriqc` is loaded from `.datalad/containers/profiles/mriqc.yaml`
2. `{img}` expands to `oci:.datalad/containers/images/mriqc/23.1.0/image`
3. `{cmd}` expands to `mriqc sourcedata/raw outputs participant --participant-label 01`
4. Full command is executed and recorded in git history

---

## Step 6: Verify Provenance

```bash
git log --oneline -1
# abc123 [DATALAD RUNCMD] apptainer exec --cleanenv ...
```

The commit message contains the exact command that ran - no hidden shims.

---

## Creating Environment-Specific Profiles

### HPC Profile with Bind Mounts

```bash
cat > .datalad/containers/profiles/mriqc-hpc.yaml << 'EOF'
extends: mriqc

exec: >-
  apptainer exec
  --cleanenv
  --bind /scratch/$USER:/scratch
  --bind /data/datasets:/data
  {img}
  {cmd}
EOF
```

### GPU-Enabled Profile

```bash
cat > .datalad/containers/profiles/mriqc-gpu.yaml << 'EOF'
extends: mriqc

exec: >-
  apptainer exec
  --cleanenv
  --nv
  {img}
  {cmd}
EOF
```

### Using Podman Instead

```bash
cat > .datalad/containers/profiles/mriqc-podman.yaml << 'EOF'
image: mriqc/23.1.0

exec: >-
  podman run
  --rm
  --userns=keep-id
  -v {pwd}:/work:Z
  -w /work
  {img}
  {cmd}
EOF
```

Use any profile:
```bash
datalad containers-run --profile mriqc-gpu ...
```

---

## Adding a New Version

```bash
# Add version 24.0.0
datalad containers-add mriqc/24.0.0 --url docker://nipreps/mriqc:24.0.0

# Create profile for new version
cat > .datalad/containers/profiles/mriqc-24.yaml << 'EOF'
extends: mriqc
image: mriqc/24.0.0
EOF

# Run with new version
datalad containers-run --profile mriqc-24 ...
```

---

## One-Off Execution Override

Don't want to create a profile? Override exec directly:

```bash
datalad containers-run \
    --image mriqc/23.1.0 \
    --exec "apptainer exec --cleanenv --nv {img} {cmd}" \
    --input sourcedata/raw \
    --output . \
    mriqc sourcedata/raw outputs participant
```

---

## Final Dataset Structure

```
mriqc-analysis/
├── .datalad/
│   └── containers/
│       ├── images/
│       │   └── mriqc/
│       │       ├── 23.1.0/
│       │       │   └── image/          # OCI directory
│       │       └── 24.0.0/
│       │           └── image/
│       └── profiles/
│           ├── mriqc.yaml
│           ├── mriqc-hpc.yaml
│           ├── mriqc-gpu.yaml
│           └── mriqc-podman.yaml
├── sourcedata/
│   └── raw/                            # BIDS input
├── outputs/                            # MRIQC results
└── workdir/                            # Ignored
```

---

## Key Points

1. **Images are just artifacts** - Downloaded once, stored in OCI format
2. **Profiles define execution** - How to invoke the container for your environment
3. **Profiles extend profiles** - Inherit and override (clobber semantics)
4. **Provenance is transparent** - Actual command recorded, not a shim
5. **Runtime override** - Use `--exec` for one-off customization
