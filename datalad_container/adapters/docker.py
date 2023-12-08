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
from pathlib import Path
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


def _get_repotag_from_image_sha256(sha):
    out = sp.check_output(
        ['docker', 'image', 'inspect', '--format',
         '{{range $v := .RepoTags}}{{$v}} {{end}}',
         sha])
    return out.decode().splitlines()[0].strip()


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


def repopulate_from_daemon(contds, imgpath: Path) -> None:
    # crude check whether anything at the image location is not
    # locally present
    contrepo = contds.repo
    if not contrepo.call_annex(
        ['find', '--not', '--in', 'here'],
        files=str(imgpath),
    ):
        # nothing is missing, we have nothing to do here
        return

    # a docker image is a collection of files in a directory
    assert imgpath.is_dir()
    # we could look into `manifest.json`, but it might also be
    # annexed and not around. instead look for the config filename
    imgcfg = [
        p.name for p in imgpath.iterdir()
        # a sha256 is 64 chars plus '.json'
        if len(p.name) == 69 and p.name.endswith('.json')
    ]
    # there is only one
    assert len(imgcfg) == 1

    # look for the employed annex backend, we need it for key reinject below
    backends = set(contrepo.call_annex_oneline([
        'find',
        f'--branch=HEAD:{imgpath.relative_to(contds.pathobj)}',
        # this needs git-annex 10.20230126 or later
        '--anything',
        # the trailing space is not a mistake!
        '--format=${backend} ',
    ]).split())
    # we can only deal with a single homogeneous backend here
    assert len(backends) == 1

    # ID is filename, minus .json extension
    img_id = imgcfg[0][:-5]

    # make an effort to get the repotags matching the image sha256
    # from docker. This is needed, because the query tag will end up
    # in manifest.json, and the original addition was likely via a tag
    # and not a sha256
    repo_tag = None
    try:
        repo_tag = _get_repotag_from_image_sha256(img_id)
    except Exception:
        # however, we will go on without a tag. In the worst case, it
        # would trigger a download of manifest.json (tiny file), but
        # the large `layer.tar` will still be successfully extracted
        # and reinject via a query by ID/sha256
        pass

    # let docker dump into a TMPDIR inside the dataset
    # this place is likely to have sufficient space
    with tempfile.TemporaryDirectory(dir=imgpath) as tmpdir:
        # try to export the image from a local docker instance
        save(
            # prefer the tag, but continue with ID (see above)
            repo_tag or f'sha256:{img_id}',
            tmpdir,
        )
        # the line above will raise an exception when
        # - this docker does not have the image.
        # - or there is not docker running at all.
        # this is fine, we will just not proceed.

        # now let git-annex reinject any file that matches a known
        # key (given the backend determined above). This will populate
        # as much as we can. This approach has built-in content verification.
        # this means that even if this docker instance has different metadata
        # we will be able to harvest any image piece that fits, and ignore
        # anything else
        contrepo.call_annex(
            ['reinject', '--known', '--backend', backends.pop()],
            files=[
                str(p) for p in Path(tmpdir).glob('**/*')
                if p.is_file()
            ],
        )


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
