"""Utilities used across the adapters
"""

import contextlib
import logging
import os
import subprocess as sp
import sys

from datalad.utils import on_windows

lgr = logging.getLogger("datalad.containers.adapters.utils")


def setup_logger(level):
    logger = logging.getLogger("datalad.containers.adapters")
    logger.setLevel(level)
    if not logger.hasHandlers():
        # If this script is executed with the file name rather than the
        # documented `python -m ...` invocation, we can't rely on DataLad's
        # handler. Add a minimal one.
        handler = logger.StreamHandler()
        handler.setFormatter(logger.Formatter('%(message)s'))
        logger.addHandler(handler)


@contextlib.contextmanager
def log_and_exit(logger):
    try:
        yield
    except Exception as exc:
        logger.exception("Failed to execute %s", sys.argv)
        if isinstance(exc, sp.CalledProcessError):
            excode = exc.returncode
            if exc.stderr:
                sys.stderr.write(exc.stderr)
        else:
            excode = 1
        sys.exit(excode)


def get_docker_image_ids():
    """Return IDs of all known images."""
    out = sp.run(
        ["docker", "images", "--all", "--quiet", "--no-trunc"],
        stdout=sp.PIPE, stderr=sp.PIPE,
        universal_newlines=True, check=True)
    return out.stdout.splitlines()


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
    sp.run(full_cmd, check=True)
