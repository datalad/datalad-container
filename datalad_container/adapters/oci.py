"""Run a container from the image in a local OCI directory.

This adapter uses Skopeo to save a Docker image (or any source that Skopeo
supports) to a local directory that's compliant with the "Open Container Image
Layout Specification" and can be tracked as objects in a DataLad dataset.

This image can then be loaded on-the-fly in order for execution. Currently only
docker-run is supported (i.e. the image is loaded with Skopeo's
"docker-daemon:" transport), but the plan is to support podman-run (via the
"containers-storage:" transport) as well.

Examples
--------

Save BusyBox 1.32 from Docker Hub to the local directory bb_1.32:

    $ python -m datalad_container.adapters.oci \\
      save docker://busybox:1.32 bb-1.32/

Load the image into the Docker daemon (if necessary) and run a command:

    $ python -m datalad_container.adapters.oci \\
      run bb_1.32/ sh -c 'busybox | head -1'
    BusyBox v1.32.0 (2020-10-12 23:47:18 UTC) multi-call binary.
"""
# ^TODO: Add note about expected image ID mismatches (e.g., between the docker
# pulled entry and loaded one)?

from collections import namedtuple
import json
import logging
from pathlib import Path
import re
import subprocess as sp
import sys

from datalad_container.adapters.utils import (
    docker_run,
    get_docker_image_ids,
    log_and_exit,
    setup_logger,
)

lgr = logging.getLogger("datalad.container.adapters.oci")

_IMAGE_SOURCE_KEY = "org.datalad.container.image.source"


def _normalize_reference(reference):
    """Normalize a short repository name to a canonical one.

    Parameters
    ----------
    reference : str
        A Docker reference (e.g., "neurodebian", "library/neurodebian").

    Returns
    -------
    A fully-qualified reference (e.g., "docker.io/library/neurodebian")

    Note: This tries to follow containers/image's splitDockerDomain().
    """
    parts = reference.split("/", maxsplit=1)
    if len(parts) == 1 or (not any(c in parts[0] for c in [".", ":"])
                           and parts[0] != "localhost"):
        domain, remainder = "docker.io", reference
    else:
        domain, remainder = parts

    if domain == "docker.io" and "/" not in remainder:
        remainder = "library/" + remainder
    return domain + "/" + remainder


Reference = namedtuple("Reference", ["name", "tag", "digest"])


def parse_docker_reference(reference, normalize=False, strip_transport=False):
    """Parse a Docker reference into a name, tag, and digest.

    Parameters
    ----------
    reference : str
        A Docker reference (e.g., "busybox" or "library/busybox:latest")
    normalize : bool, optional
        Whether to normalize short names like "busybox" to the fully qualified
        name ("docker.io/library/busybox")
    strip_transport : bool, optional
        Remove Skopeo transport value ("docker://" or "docker-daemon:") from
        the name. Unless this is true, reference should not include a
        transport.

    Returns
    -------
    A Reference namedtuple with .name, .tag, and .digest attributes
    """
    if strip_transport:
        try:
            reference = reference.split(":", maxsplit=1)[1]
        except IndexError:
            raise ValueError("Reference did not have transport: {}"
                             .format(reference))
        if reference.startswith("//"):
            reference = reference[2:]

    parts = reference.split("/")
    last = parts[-1]
    if "@" in last:
        sep = "@"
    elif ":" in last:
        sep = ":"
    else:
        sep = None

    tag = None
    digest = None
    if sep:
        repo, label = last.split(sep)
        front = "/".join(parts[:-1] + [repo])
        if sep == "@":
            digest = label
        else:
            tag = label
    else:
        front, tag = "/".join(parts), None
    if normalize:
        front = _normalize_reference(front)
    return Reference(front, tag, digest)


def _store_annotation(path, key, value):
    """Set a value of image's org.datalad.container.image.source annotation.

    Parameters
    ----------
    path : pathlib.Path
        Image directory. It must contain only one image.
    key, value : str
        Key and value to store in the image's "annotations" field.
    """
    index = path / "index.json"
    index_info = json.loads(index.read_text())
    annot = index_info["manifests"][0].get("annotations", {})

    annot[key] = value
    index_info["manifests"][0]["annotations"] = annot
    with index.open("w") as fh:
        json.dump(index_info, fh)


def _get_annotation(path, key):
    """Return value for `key` in an image's annotation.

    Parameters
    ----------
    path : pathlib.Path
        Image directory. It must contain only one image.
    key : str
        Key in the image's "annotations" field.

    Returns
    -------
    str or None
    """
    index = path / "index.json"
    index_info = json.loads(index.read_text())
    # Assume one manifest because skopeo-inspect would fail anyway otherwise.
    return index_info["manifests"][0].get("annotations", {}).get(key)


def save(image, path):
    """Save an image to an OCI-compliant directory.

    Parameters
    ----------
    image : str
        A source image accepted by skopeo-copy
    path : pathlib.Path
        Directory to copy the image to
    """
    # Refuse to work with non-empty directory if it's not empty by letting the
    # OSError through. Multiple images can be saved to an OCI directory, but
    # run() and get_image_id() don't support a way to pull out a specific one.
    try:
        path.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise OSError(exc) from None
    path.mkdir(parents=True)
    dest = "oci:" + str(path)
    tag = parse_docker_reference(image).tag
    if tag:
        dest += ":" + tag
    sp.run(["skopeo", "copy", image, dest], check=True)
    _store_annotation(path, _IMAGE_SOURCE_KEY, image)


def get_image_id(path):
    """Return a directory's image ID.

    Parameters
    ----------
    path : pathlib.Path
        Image directory. It must contain only one image.

    Returns
    -------
    An image ID (str)
    """
    # Note: This adapter depends on one image per directory. If, outside of
    # this adapter interface, multiple images were stored in a directory, this
    # will inspect call fails with a reasonable message.
    res = sp.run(["skopeo", "inspect", "--raw", "oci:" + str(path)],
                 stdout=sp.PIPE, stderr=sp.PIPE,
                 universal_newlines=True, check=True)
    info = json.loads(res.stdout)
    return info["config"]["digest"]


def load(path):
    """Load OCI image from `path`.

    Currently the only supported load destination is the Docker daemon.

    Parameters
    ----------
    path : pathlib.Path
        An OCI-compliant directory such as the one generated by `save`. It must
        contain only one image.

    Returns
    -------
    An image ID (str)
    """
    image_id = get_image_id(path)
    if image_id not in get_docker_image_ids():
        lgr.debug("Loading %s", image_id)
        # The image is copied with a datalad-container/ prefix to reduce the
        # chance of collisions with existing names registered with the Docker
        # daemon. While we must specify _something_ for the name and tag in
        # order to copy it, the particular values don't matter for execution
        # purposes; they're chosen to help users identify the container in the
        # `docker images` output.
        source = _get_annotation(path, _IMAGE_SOURCE_KEY)
        if source:
            ref = parse_docker_reference(source, strip_transport=True)
            name = ref.name
            if ref.tag:
                tag = ref.tag
            else:
                if ref.digest:
                    tag = "source-" + ref.digest.replace(":", "-")[:14]
                else:
                    tag = "latest"

        else:
            name = re.sub("[^a-z0-9-_.]", "", path.name.lower()[:10])
            tag = image_id.replace(":", "-")[:14]

        lgr.debug("Copying %s to Docker daemon", image_id)
        sp.run(["skopeo", "copy", "oci:" + str(path),
                # This load happens right before the command executes. Don't
                # let the output be confused for the command's output.
                "--quiet",
                "docker-daemon:datalad-container/{}:{}".format(name, tag)],
               check=True)
    else:
        lgr.debug("Image %s is already present", image_id)
    return image_id


# Command-line


def cli_save(namespace):
    save(namespace.image, namespace.path)


def cli_run(namespace):
    image_id = load(namespace.path)
    docker_run(image_id, namespace.cmd)


def main(args):
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m datalad_container.adapters.oci",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v", "--verbose",
        action="store_true")

    subparsers = parser.add_subparsers(title="subcommands")
    # Don't continue without a subcommand.
    subparsers.required = True
    subparsers.dest = "command"

    parser_save = subparsers.add_parser(
        "save",
        help="save an image to a directory")
    parser_save.add_argument(
        "image", metavar="NAME",
        help="image to save")
    parser_save.add_argument(
        "path", metavar="PATH", type=Path,
        help="directory to save image in")
    parser_save.set_defaults(func=cli_save)

    parser_run = subparsers.add_parser(
        "run",
        help="run a command with a directory's image")

    # TODO: Support containers-storage/podman. This would need to be fed
    # through cli_run() and load(). Also, a way to specify it should probably
    # be available through containers-add.
    # parser_run.add_argument(
    #     "--dest", metavar="TRANSPORT",
    #     choices=["docker-daemon", "containers-storage"],
    #     ...)
    parser_run.add_argument(
        "path", metavar="PATH", type=Path,
        help="image directory")
    parser_run.add_argument(
        "cmd", metavar="CMD", nargs=argparse.REMAINDER,
        help="command to execute")
    parser_run.set_defaults(func=cli_run)

    namespace = parser.parse_args(args[1:])

    setup_logger(logging.DEBUG if namespace.verbose else logging.INFO)

    namespace.func(namespace)


if __name__ == "__main__":
    with log_and_exit(lgr):
        main(sys.argv)
