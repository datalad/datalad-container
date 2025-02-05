import hashlib
import json
from pathlib import Path

from datalad.api import ls_file_collection


def descriptor(record):
    """Create an OSI-compliant descriptor from a file collection record

    This translates a DataLad ls_file_collection record into a minimal OCI
    content descriptor. The media types are based on an example image
    saved with Docker v27 (n=1 sample size), and they are assigned based on
    the file extensions alone. The gzipped variant appears in the OCI spec
    but the file extensions are a complete guess here.
    """
    media_type = None
    p = record["item"]
    if p.suffix == ".json":
        media_type = "application/vnd.docker.container.image.v1+json"
    elif p.suffix == ".tar":
        media_type = "application/vnd.docker.image.rootfs.diff.tar"
    elif p.suffix in {".tgz", ".tar.gz", ".tar.gzip"}:
        media_type = "application/vnd.docker.image.rootfs.diff.tar+gzip"

    d = {
        "mediaType": media_type,
        "digest": f"sha256:{record['hash-sha256']}",
        "size": record["size"],
    }
    return d


def new_manifest(path):
    """Create a v2 docker image manifest from an old saved image

    This is a best effort of creating a "new style" OSI-compliant image
    manifest from an image saved with an older (<25) Docker version.
    Such manifest may be needed to compute the image ID for Docker >=27.

    """
    # use ls_file_collection to get sizes and hashes of container files
    # we do not need all, but hashing the text files adds little overhead
    # and the convenience probably wins
    records = ls_file_collection(
        type="annexworktree",
        collection=path.absolute(),
        hash="sha256",
        result_renderer="disabled"
    )

    # we only need certain files, in the order they appear in old manifest
    # convert the above to a path-indexed dict for easier lookups
    contents = {r["item"].relative_to(r["collection"]): r for r in records}

    # read the old manifest and find out the config and layer paths
    with path.joinpath("manifest.json").open("rb") as jpath:
        manifest = json.load(jpath)[0]
    config_path = Path(manifest["Config"])
    layer_paths = [Path(layer) for layer in manifest["Layers"]]

    # create the new-style manifest
    d = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": descriptor(contents[config_path]),
        "layers": [descriptor(contents[p]) for p in layer_paths],
    }

    return json.dumps(d, separators=(",", ":"))


def get_image_id(path, repo_tag=None, config=None):
    """Return the ID of an image extracted at path.

    This is a drop-in replacement for get_image which tries to emulate
    Docker 27 behavior when creating image IDs seemingly based on the
    hash of the v2 image manifest (even if the image is stored in an
    older format, in which case we try to create a manifest ourselves).
    It does not take all the combinatorics ino account but can serve as
    a workaround in at least some cases.

    """
    if (repo_tag is not None) or (config is not None):
        msg = (
            "Dealing with repo tags or config is not implemented"
            "for the new style of docker manifests"
        )
        raise NotImplementedError(msg)

    if isinstance(path, str):
        path = Path(path)

    # determine "new" vs "old" schema
    with path.joinpath("manifest.json").open() as jpath:
        manifest = json.load(jpath)

    try:
        isNewSchema = manifest.get("schemaVersion", 1) >= 2
    except AttributeError:
        isNewSchema = False

    # get a hash of a new-style manifest, generating one if needed
    if isNewSchema:
        shasum = hashlib.sha256(path.read_bytes())
    else:
        nm = new_manifest(path)
        shasum = hashlib.sha256(nm.encode("utf-8")).hexdigest()

    return f"sha256:{shasum}"
