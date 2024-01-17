"""Collection of common utilities"""

from __future__ import annotations

# the pathlib equivalent is only available in PY3.12
from os.path import lexists
from pathlib import (
    PurePath,
    PurePosixPath,
    PureWindowsPath,
)

from datalad.distribution.dataset import Dataset
from datalad.support.external_versions import external_versions


def get_container_command():
    for command in ["apptainer", "singularity"]:
        container_system_version = external_versions[f"cmd:{command}"]
        if container_system_version:
            return command
    else:
        raise RuntimeError("Did not find apptainer or singularity")


def get_container_configuration(
    ds: Dataset,
    name: str | None = None,
) -> dict:
    """Report all container-related configuration in a dataset

    Such configuration is identified by the item name pattern::

      datalad.containers.<container-name>.<item-name>

    Parameters
    ----------
    ds: Dataset
      Dataset instance to report configuration on.
    name: str, optional
      If given, the reported configuration will be limited to the container
      with this exact name. In this case, only a single ``dict`` is returned,
      not nested dictionaries.

    Returns
    -------
    dict
      Keys are the names of configured containers and values are dictionaries
      with their respective configuration items (with the
      ``datalad.containers.<container-name>.`` prefix removed from their
      keys).
      If `name` is given, only a single ``dict`` with the configuration
      items of the matching container is returned (i.e., there will be no
      outer ``dict`` with container names as keys).
      If not (matching) container configuration exists, and empty dictionary
      is returned.
    """
    var_prefix = 'datalad.containers.'

    containers = {}
    # all info is in the dataset config!
    for var, value in ds.config.items():
        if not var.startswith(var_prefix):
            # not an interesting variable
            continue
        var_comps = var.split('.')
        # container name is the 3rd after 'datalad'.'container'.
        cname = var_comps[2]
        if name and name != cname:
            # we are looking for a specific container's configuration
            # and this is not it
            continue
        # reconstruct config item name, anything after
        # datalad.containers.<name>.
        ccfgname = '.'.join(var_comps[3:])
        if not ccfgname:
            continue

        if ccfgname == 'image':
            # run image path normalization to get a relative path
            # in platform conventions, regardless of the input.
            # for now we report a str, because the rest of the code
            # is not using pathlib
            value = str(_normalize_image_path(value, ds))

        cinfo = containers.get(cname, {})
        cinfo[ccfgname] = value

        containers[cname] = cinfo

    return containers if name is None else containers.get(name, {})


def _normalize_image_path(path: str, ds: Dataset) -> PurePath:
    """Helper to standardize container image path handling

    Previously, container configuration would contain platform-paths
    for container image location (e.g., windows paths when added on
    windows, POSIX paths elsewhere). This made cross-platform reuse
    impossible out-of-the box, but it also means that such dataset
    are out there in unknown numbers.

    This helper inspects an image path READ FROM CONFIG(!) and ensures
    that it matches platform conventions (because all other arguments)
    also come in platform conventions. This enables standardizing
    the storage conventions to be POSIX-only (for the future).

    Parameters
    ----------
    path: str
      A str-path, as read from the configuration, matching its conventions
      (relative path, pointing to a container image relative to the
      dataset's root).
    ds: Dataset
      This dataset's base path is used as a reference for resolving
      the relative image path to an absolute location on the file system.

    Returns
    -------
    PurePath
      Relative path in platform conventions
    """
    # we only need to act differently, when an incoming path is
    # windows. This is not possible to say with 100% confidence,
    # because a POSIX path can also contain a backslash. We support
    # a few standard cases where we CAN tell
    pathobj = None
    if '\\' not in path:
        # no windows pathsep, no problem
        pathobj = PurePosixPath(path)
    elif path.startswith(r'.datalad\\environments\\'):
        # this is the default location setup in windows conventions
        pathobj = PureWindowsPath(path)
    else:
        # let's assume it is windows for a moment
        if lexists(str(ds.pathobj / PureWindowsPath(path))):
            # if there is something on the filesystem for this path,
            # we can be reasonably sure that this is indeed a windows
            # path. This won't catch images in uninstalled subdataset,
            # but better than nothing
            pathobj = PureWindowsPath(path)
        else:
            # if we get here, we have no idea, and no means to verify
            # further hypotheses -- go with the POSIX assumption
            # and hope for the best
            pathobj = PurePosixPath(path)

    assert pathobj is not None
    # we report in platform-conventions
    return PurePath(pathobj)
