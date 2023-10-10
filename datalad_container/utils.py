"""Collection of common utilities"""

from __future__ import annotations

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

        cinfo = containers.get(cname, {})
        cinfo[ccfgname] = value

        containers[cname] = cinfo

    return containers if name is None else containers.get(name, {})
