"""Work with Docker images as local paths.

This module provides support for saving a Docker image in a local directory and
then loading it on-the-fly before calling `docker run ...`. The motivation for
this is that it allows the components of an image to be tracked as objects in a
DataLad dataset.

Run `python -m datalad_container.adapters.docker --help` for details about the
command-line interface.
"""

import hashlib
import json
import os
import os.path as op
import subprocess as sp
import sys
import tarfile
import tempfile

import logging

from datalad.utils import (
    on_windows,
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


def _list_images():
    out = sp.check_output(
        ["docker", "images", "--all", "--quiet", "--no-trunc"])
    return out.decode().splitlines()


def get_image(path, repo_tag=None, config=None):
    """Return the image ID of the image extracted at `path`.
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

    with open(op.join(path, manifest[0]["Config"]), "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def load(path, repo_tag, config):
    """Load the Docker image from `path`.

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
    The image ID (str)
    """
    # FIXME: If we load a dataset, it may overwrite the current tag. Say that
    # (1) a dataset has a saved neurodebian:latest from a month ago, (2) a
    # newer neurodebian:latest has been pulled, and (3) the old image have been
    # deleted (e.g., with 'docker image prune --all'). Given all three of these
    # things, loading the image from the dataset will tag the old neurodebian
    # image as the latest.
    image_id = "sha256:" + get_image(path, repo_tag, config)
    if image_id not in _list_images():
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

    if image_id not in _list_images():
        raise RuntimeError(
            "docker image {} was not successfully loaded".format(image_id))
    return image_id


# Command-line


def cli_save(namespace):
    save(namespace.image, namespace.path)


def cli_run(namespace):
    image_id = load(namespace.path, namespace.repo_tag, namespace.config)
    prefix = ["docker", "run",
              # FIXME: The -v/-w settings are convenient for testing, but they
              # should be configurable.
              "-v", "{}:/tmp".format(os.getcwd()),
              "-w", "/tmp",
              "--rm",
              "--interactive"]
    if not on_windows:
        # Make it possible for the output files to be added to the
        # dataset without the user needing to manually adjust the
        # permissions.
        prefix.extend(["-u", "{}:{}".format(os.getuid(), os.getgid())])

    if sys.stdin.isatty():
        prefix.append("--tty")
    prefix.append(image_id)
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
