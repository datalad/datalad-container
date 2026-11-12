# Example: MRIQC Workflow with ReproNim/containers

This example demonstrates using ReproNim/containers as a subdataset to run MRIQC for MRI quality control. We extend the provided base profile with our own environment-specific settings.

---

## Prerequisites

```bash
# Install datalad and extensions
pip install datalad datalad-container

# Install a container runtime (at least one)
# Apptainer (recommended for HPC)
sudo apt-get install apptainer

# Or Podman (rootless Docker alternative)
sudo apt-get install podman

# Install Skopeo for OCI image fetching
sudo apt-get install skopeo
```

---

## Step 1: Create Your Analysis Dataset

Following YODA principles, create a dataset that will contain everything needed for the analysis.

```bash
# Create the analysis dataset
datalad create -c text2git mriqc-analysis
cd mriqc-analysis
```

---

## Step 2: Install ReproNim Containers

```bash
# Install the containers collection as a subdataset
datalad install -d . -s https://github.com/ReproNim/containers code/containers

# List available images
datalad containers-images -d code/containers
# mriqc/23.1.0
# mriqc/24.0.0
# fmriprep/23.2.0
# ...

# List available profiles
datalad containers-profiles -d code/containers
# mriqc
# fmriprep
# ...
```

---

## Step 3: Install Input Data

```bash
# Install demo BIDS dataset
datalad install -d . -s https://github.com/ReproNim/ds000003-demo sourcedata/raw
```

---

## Step 4: Create Your Execution Profile

ReproNim provides a base profile, but we need to customize it for our environment.

```bash
# Create profiles directory
mkdir -p .datalad/containers/profiles

# Create our lab-specific profile
cat > .datalad/containers/profiles/mriqc-dartmouth.yaml << 'EOF'
# MRIQC profile for Dartmouth HPC (Discovery cluster)

extends: code/containers/.datalad/containers/profiles/mriqc.yaml

# Clobber the exec with our environment-specific settings
exec: >-
  apptainer exec
  --cleanenv
  --bind /scratch/$USER:/scratch
  --bind /dartfs-hpc/rc/lab/mylab:/data
  {img}
  {cmd}
EOF

# Commit the profile
datalad save -m "Add Dartmouth-specific MRIQC profile"
```

**What's happening here:**
- We extend ReproNim's base `mriqc` profile
- We clobber `exec` with our HPC-specific bind mounts
- The `{img}` placeholder will resolve to the OCI image path
- The `{cmd}` placeholder will be replaced with the actual command

---

## Step 5: Ignore Working Directory

MRIQC needs a working directory for intermediate files:

```bash
echo "workdir/" > .gitignore
datalad save -m "Ignore workdir" .gitignore
```

---

## Step 6: Run the Analysis

```bash
# Run MRIQC using our custom profile
datalad containers-run \
    --profile mriqc-dartmouth \
    --input sourcedata/raw \
    --output . \
    mriqc /data/bids /data/outputs participant group -w /scratch/workdir
```

**What happens:**
1. Profile is resolved: `mriqc-dartmouth` → extends `mriqc` → references `mriqc/23.1.0`
2. Image is fetched if needed (OCI layers from Docker Hub)
3. `{img}` expands to `oci:.datalad/containers/images/mriqc/23.1.0/image`
4. `{cmd}` expands to `mriqc /data/bids /data/outputs participant group -w /scratch/workdir`
5. Full command is executed and recorded in provenance

---

## Step 7: Verify Provenance

```bash
git log --oneline -1
# abc123 [DATALAD RUNCMD] apptainer exec --cleanenv --bind ...

git show --quiet
```

**Provenance shows the actual command:**
```json
{
  "cmd": "apptainer exec --cleanenv --bind /scratch/$USER:/scratch --bind /dartfs-hpc/rc/lab/mylab:/data oci:.datalad/containers/images/mriqc/23.1.0/image mriqc /data/bids /data/outputs participant group -w /scratch/workdir",
  "profile": "mriqc-dartmouth",
  "profile-source": ".datalad/containers/profiles/mriqc-dartmouth.yaml",
  "inputs": ["sourcedata/raw"],
  "outputs": ["."]
}
```

No shims. No hidden behavior. The exact command that ran.

---

## Alternative: One-Off Execution

If you don't want to create a profile, you can override exec directly:

```bash
datalad containers-run \
    -d code/containers \
    --profile mriqc \
    --exec "apptainer exec --cleanenv --nv {img} {cmd}" \
    --input sourcedata/raw \
    --output . \
    mriqc sourcedata/raw . participant --participant-label 01
```

---

## Alternative: GPU-Enabled Run

Create a GPU profile for compute-intensive jobs:

```bash
cat > .datalad/containers/profiles/mriqc-gpu.yaml << 'EOF'
extends: code/containers/.datalad/containers/profiles/mriqc.yaml

exec: >-
  apptainer exec
  --cleanenv
  --nv
  --bind /scratch/$USER:/scratch
  {img}
  {cmd}
EOF

datalad save -m "Add GPU-enabled MRIQC profile"

# Use it
datalad containers-run \
    --profile mriqc-gpu \
    --input sourcedata/raw \
    --output . \
    mriqc sourcedata/raw . participant
```

---

## Alternative: Using Podman Instead

```bash
cat > .datalad/containers/profiles/mriqc-podman.yaml << 'EOF'
extends: code/containers/.datalad/containers/profiles/mriqc.yaml

exec: >-
  podman run
  --rm
  --userns=keep-id
  -v {pwd}:/work:Z
  -w /work
  {img}
  {cmd}
EOF

datalad save -m "Add Podman MRIQC profile"

datalad containers-run \
    --profile mriqc-podman \
    --input sourcedata/raw \
    --output . \
    mriqc /work/sourcedata/raw /work/outputs participant
```

---

## Step 8: Update to Newer Version

To use a newer MRIQC version:

```bash
# Create profile pointing to newer version
cat > .datalad/containers/profiles/mriqc-24.yaml << 'EOF'
extends: code/containers/.datalad/containers/profiles/mriqc.yaml

# Override image to use version 24
image: mriqc/24.0.0

exec: >-
  apptainer exec
  --cleanenv
  --bind /scratch/$USER:/scratch
  {img}
  {cmd}
EOF

datalad save -m "Add MRIQC 24.0.0 profile"

# Run with new version
datalad containers-run \
    --profile mriqc-24 \
    --input sourcedata/raw \
    --output outputs-v24 \
    mriqc sourcedata/raw outputs-v24 participant
```

---

## Final Dataset Structure

```
mriqc-analysis/
├── .datalad/
│   └── containers/
│       └── profiles/
│           ├── mriqc-dartmouth.yaml
│           ├── mriqc-gpu.yaml
│           └── mriqc-podman.yaml
├── .gitignore
├── code/
│   └── containers/              # ReproNim/containers subdataset
│       └── .datalad/containers/
│           ├── images/
│           │   └── mriqc/
│           │       ├── 23.1.0/
│           │       │   └── image/
│           │       └── 24.0.0/
│           │           └── image/
│           └── profiles/
│               └── mriqc.yaml   # Base profile we extend
├── sourcedata/
│   └── raw/                     # ds000003-demo subdataset
├── outputs/                     # MRIQC outputs
└── workdir/                     # Ignored working directory
```

---

## Key Takeaways

1. **Profiles are explicit** - You see exactly what will run
2. **Profiles are composable** - Extend base profiles with your settings
3. **Clobber semantics** - Your `exec` replaces the parent's entirely
4. **Provenance is complete** - The actual command is recorded, not a shim
5. **Environment-specific** - Each lab/HPC can have its own profile
6. **Version-controlled** - Profiles are committed with your analysis

---

## Troubleshooting

**"Image not found"**
```bash
# Check if image exists
ls code/containers/.datalad/containers/images/mriqc/

# Fetch if needed
datalad get code/containers/.datalad/containers/images/mriqc/23.1.0/
```

**"Permission denied" with Apptainer**
```bash
# Check bind mount permissions
ls -la /scratch/$USER

# Ensure OCI directory is readable
ls -la code/containers/.datalad/containers/images/mriqc/23.1.0/image/
```

**Profile not found**
```bash
# List available profiles
datalad containers-profiles

# Check profile syntax
cat .datalad/containers/profiles/mriqc-dartmouth.yaml
```
