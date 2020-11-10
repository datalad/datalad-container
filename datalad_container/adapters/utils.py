"""Utilities used across the adapters
"""

import logging
import os
import subprocess as sp
import sys

from datalad.utils import on_windows

lgr = logging.getLogger("datalad.containers.adapters.utils")


def get_docker_image_ids():
    """Return IDs of all known images."""
    out = sp.check_output(
        ["docker", "images", "--all", "--quiet", "--no-trunc"])
    return out.decode().splitlines()


def docker_run(image_id, cmd):
    """Execute `docker run`.

    Parameters
    ----------
    image_id : str
        ID of image to execute
    cmd : list of str
        Command to execute
    """
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
    full_cmd = prefix + cmd
    lgr.debug("Running %r", full_cmd)
    sp.check_call(full_cmd)