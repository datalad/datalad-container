"""Work with Docker images as local paths.

This module provides support for saving a Docker image in a local directory and
then loading it on-the-fly before calling `docker run ...`. The motivation for
this is that it allows the components of an image to be tracked as objects in a
DataLad dataset.

Run `python -m datalad_container.adapters.docker --help` for details about the
command-line interface.
"""

import hashlib
import io
import json
import logging
import os
import os.path as op
import subprocess as sp
import sys
import tarfile
import tempfile

from datalad.utils import on_windows

lgr = logging.getLogger("datalad.containers.adapters.docker")

# Note: A dockerpy dependency probably isn't worth it in the current
# state but is worth thinking about if this module gets more
# complicated.

# FIXME: These functions assume that there is a "docker" on the path
# that can be managed by a non-root user.  At the least, this should
# be documented somewhere.


def save(image, path):
    """Save and extract a docker image to a directory.

    Parameters
    ----------
    image : str
        A unique identifier for a docker image.
    path : str
        A directory to extract the image to.
    """
    # Use a temporary file because docker save (or actually tar underneath)
    # complains that stdout needs to be redirected if we use Popen and PIPE.
    if ":" not in image:
        image = f"{image}:latest"
    with tempfile.NamedTemporaryFile() as stream:
        # Windows can't write to an already opened file
        stream.close()
        sp.check_call(["docker", "save", "-o", stream.name, image])
        with tarfile.open(stream.name, mode="r:") as tar:
            if not op.exists(path):
                lgr.debug("Creating new directory at %s", path)
                os.makedirs(path)
            elif os.listdir(path):
                raise OSError("Directory {} is not empty".format(path))
            def is_within_directory(directory, target):

                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)

                prefix = os.path.commonprefix([abs_directory, abs_target])

                return prefix == abs_directory

            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):

                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")

                tar.extractall(path, members, numeric_owner=numeric_owner)


            safe_extract(tar, path=path)
            lgr.info("Saved %s to %s", image, path)


def _get_layers(ref):
    """Return the layers (diff IDs) of image `ref`, None if Docker has none
    """
    p = sp.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}",
         ref],
        stdout=sp.PIPE, stderr=sp.PIPE)
    if p.returncode:
        return None
    return json.loads(p.stdout) or []


def _get_manifest_entry(path, repo_tag=None, config=None):
    """Return the manifest.json entry of the image extracted at `path`.
    """
    manifest_path = op.join(path, "manifest.json")
    with open(manifest_path) as fp:
        manifest = json.load(fp)
    if repo_tag is not None:
        manifest = [img for img in manifest if repo_tag in (img.get("RepoTags") or [])]
    if config is not None:
        manifest = [img for img in manifest if img["Config"].startswith(config)]
    if len(manifest) == 0:
        raise ValueError(f"No matching images found in {manifest_path}")
    elif len(manifest) > 1:
        raise ValueError(
            f"Multiple images found in {manifest_path}; disambiguate with"
            " --repo-tag or --config"
        )
    return manifest[0]


def get_image(path, repo_tag=None, config=None):
    """Return the image ID of the image extracted at `path`.

    This is the digest of the image's configuration, which is the image ID
    for Docker's classic image store, but not for Docker's containerd image
    store, the default since Docker 29; see `load()`.
    """
    entry = _get_manifest_entry(path, repo_tag, config)
    with open(op.join(path, entry["Config"]), "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _has_config(path, descriptor, config_digest):
    """Whether an OCI descriptor in `path` leads to an image with the config
    of digest `config_digest`
    """
    algo, _, digest = descriptor.get("digest", "").partition(":")
    blob = op.join(path, "blobs", algo, digest)
    if not op.isfile(blob):
        # e.g. an image index lists the manifests for all platforms, but
        # only those for the local platform are saved
        return False
    if op.getsize(blob) > 4 * 1024 * 1024:
        # not a manifest or an image index, which are small JSON documents
        return False
    with open(blob) as fp:
        try:
            content = json.load(fp)
        except ValueError:
            return False
    if not isinstance(content, dict):
        return False
    if "manifests" in content:
        # an image index
        return any(_has_config(path, d, config_digest)
                   for d in content["manifests"])
    return (content.get("config") or {}).get("digest") == config_digest


def _get_index(path, config_digest):
    """Return the index.json of the OCI layout in `path` (saved by Docker >=
    25), limited to the descriptors that lead to the image with the config
    of digest `config_digest`, or None if there are none
    """
    index_path = op.join(path, "index.json")
    if not op.exists(index_path):
        return None
    with open(index_path) as fp:
        try:
            index = json.load(fp)
        except ValueError:
            lgr.debug("Ignoring %s, which is not valid JSON", index_path)
            return None
    if not isinstance(index, dict):
        return None
    manifests = [d for d in index.get("manifests") or []
                 if _has_config(path, d, config_digest)]
    return dict(index, manifests=manifests) if manifests else None


def load(path, repo_tag, config):
    """Load the Docker image from `path`.

    The image is loaded as, and only tagged with, the reference
    "datalad-container:<digest of its configuration>" (see `get_image()`),
    unless an image of that reference with the image's layers is present
    already.  It is not identified by its image ID, as that depends on
    Docker's image store and, with the containerd one, on how the image was
    loaded.

    Parameters
    ----------
    path : str
        A directory with an extracted tar archive.
    repo_tag : str or None
        `image:tag` of image to load
    config : str or None
        "Config" value or prefix of image to load

    Returns
    -------
    The image's reference (str)
    """
    entry = _get_manifest_entry(path, repo_tag, config)
    with open(op.join(path, entry["Config"]), "rb") as stream:
        image_config = stream.read()
    digest = hashlib.sha256(image_config).hexdigest()
    layers = json.loads(image_config)["rootfs"]["diff_ids"]
    ref = "datalad-container:" + digest
    if _get_layers(ref) == layers:
        lgr.debug("Image %s is already present", ref)
        return ref

    lgr.debug("Loading %s", ref)
    # Have `docker load` tag the image as `ref` only, rather than re-pointing
    # the tags it was saved with, by replacing the files that name it in the
    # stream (None leaves a file out): manifest.json, which the classic image
    # store takes the tags from, and the index.json of an OCI layout (saved
    # by Docker >= 25), which the containerd image store takes a fully
    # qualified name from.  Without a usable index.json, leave out the OCI
    # layout, so that the containerd image store uses manifest.json too.
    # Leave out the legacy "repositories" file, which also names the image.
    files = {"manifest.json": [dict(entry, RepoTags=[ref])],
             "repositories": None}
    index = _get_index(path, "sha256:" + digest)
    if index is None:
        files.update({"index.json": None, "oci-layout": None})
    else:
        for descriptor in index["manifests"]:
            descriptor["annotations"] = dict(
                descriptor.get("annotations") or {},
                **{"io.containerd.image.name": "docker.io/library/" + ref,
                   "org.opencontainers.image.ref.name": digest})
        files["index.json"] = index
    cmd = ["docker", "load"]
    p = sp.Popen(cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    with tarfile.open(fileobj=p.stdin, mode="w|", dereference=True) as tar:
        tar.add(path, arcname="",
                filter=lambda info: None if info.name in files else info)
        for name, content in files.items():
            if content is not None:
                data = json.dumps(content).encode()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    out, err = p.communicate()
    return_code = p.poll()
    if return_code:
        lgr.warning("Running %r failed: %s", cmd, err.decode())
        raise sp.CalledProcessError(return_code, cmd, output=out)

    if _get_layers(ref) != layers:
        raise RuntimeError(
            "docker image {} was not successfully loaded".format(ref))
    return ref


# Command-line


def cli_save(namespace):
    save(namespace.image, namespace.path)


def cli_run(namespace):
    ref = load(namespace.path, namespace.repo_tag, namespace.config)
    prefix = ["docker", "run",
              # FIXME: The -v/-w settings are convenient for testing, but they
              # should be configurable.
              "-v", "{}:/tmp".format(os.getcwd()),
              "-w", "/tmp",
              "--rm",
              # run the image just loaded, never one pulled under its name
              "--pull=never",
              "--interactive"]
    if not on_windows:
        # Make it possible for the output files to be added to the
        # dataset without the user needing to manually adjust the
        # permissions.
        prefix.extend(["-u", "{}:{}".format(os.getuid(), os.getgid())])

    if sys.stdin.isatty():
        prefix.append("--tty")
    prefix.append(ref)
    cmd = prefix + namespace.cmd
    lgr.debug("Running %r", cmd)
    sp.check_call(cmd)


def main(args):
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m datalad_container.adapters.docker",
        description="Work with Docker images as local paths")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true")

    subparsers = parser.add_subparsers(title="subcommands")
    # Don't continue without a subcommand.
    subparsers.required = True
    subparsers.dest = "command"

    parser_save = subparsers.add_parser(
        "save",
        help="save and extract a Docker image to a directory")
    parser_save.add_argument(
        "image", metavar="NAME",
        help="image to save")
    parser_save.add_argument(
        "path", metavar="PATH",
        help="directory to save image in")
    parser_save.set_defaults(func=cli_save)
    # TODO: Add command for updating an archive directory.

    parser_run = subparsers.add_parser(
        "run",
        help="run a command with a directory's image")
    parser_run.add_argument(
        "--repo-tag", metavar="IMAGE:TAG", help="Tag of image to load"
    )
    parser_run.add_argument(
        "--config",
        metavar="IDPREFIX",
        help="Config value or prefix of image to load"
    )
    parser_run.add_argument(
        "path", metavar="PATH",
        help="run the image in this directory")
    parser_run.add_argument(
        "cmd", metavar="CMD", nargs=argparse.REMAINDER,
        help="command to execute")
    parser_run.set_defaults(func=cli_run)

    namespace = parser.parse_args(args[1:])

    logging.basicConfig(
        level=logging.DEBUG if namespace.verbose else logging.INFO,
        format="%(message)s")

    namespace.func(namespace)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception as exc:
        lgr.exception("Failed to execute %s", sys.argv)
        if isinstance(exc, sp.CalledProcessError):
            excode = exc.returncode
        else:
            excode = 1
        sys.exit(excode)
