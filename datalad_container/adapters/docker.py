"""Work with Docker images as local paths.

This module provides support for saving a Docker image in a local directory and
then loading it on-the-fly before calling `docker run ...`. The motivation for
this is that it allows the components of an image to be tracked as objects in a
DataLad dataset.

Run `python -m datalad_container.adapters.docker --help` for details about the
command-line interface.
"""

from glob import glob
import hashlib
import os
import os.path as op
import subprocess as sp
import sys
import tarfile
import tempfile

import logging

from datalad_container.adapters.utils import (
    docker_run,
    get_docker_image_ids,
    log_and_exit,
    setup_logger,
)

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
    with tempfile.NamedTemporaryFile() as stream:
        # Windows can't write to an already opened file
        stream.close()
        sp.run(["docker", "save", "-o", stream.name, image], check=True)
        with tarfile.open(stream.name, mode="r:") as tar:
            if not op.exists(path):
                lgr.debug("Creating new directory at %s", path)
                os.makedirs(path)
            elif os.listdir(path):
                raise OSError("Directory {} is not empty".format(path))
            tar.extractall(path=path)
            lgr.info("Saved %s to %s", image, path)


def get_image(path):
    """Return the image ID of the image extracted at `path`.
    """
    jsons = [j for j in glob(op.join(path, "*.json"))
             if not j.endswith(op.sep + "manifest.json")]
    if len(jsons) != 1:
        raise ValueError("Could not find a unique JSON configuration object "
                         "in {}".format(path))

    with open(jsons[0], "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def load(path):
    """Load the Docker image from `path`.

    Parameters
    ----------
    path : str
        A directory with an extracted tar archive.

    Returns
    -------
    The image ID (str)
    """
    # FIXME: If we load a dataset, it may overwrite the current tag. Say that
    # (1) a dataset has a saved neurodebian:latest from a month ago, (2) a
    # newer neurodebian:latest has been pulled, and (3) the old image have been
    # deleted (e.g., with 'docker image prune --all'). Given all three of these
    # things, loading the image from the dataset will tag the old neurodebian
    # image as the latest.
    image_id = "sha256:" + get_image(path)
    if image_id not in get_docker_image_ids():
        lgr.debug("Loading %s", image_id)
        cmd = ["docker", "load"]
        p = sp.Popen(cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
        with tarfile.open(fileobj=p.stdin, mode="w|", dereference=True) as tar:
            tar.add(path, arcname="")
        out, err = p.communicate()
        return_code = p.poll()
        if return_code:
            lgr.warning("Running %r failed: %s", cmd, err.decode())
            raise sp.CalledProcessError(return_code, cmd, output=out)
    else:
        lgr.debug("Image %s is already present", image_id)

    if image_id not in get_docker_image_ids():
        raise RuntimeError(
            "docker image {} was not successfully loaded".format(image_id))
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
        "path", metavar="PATH",
        help="run the image in this directory")
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
