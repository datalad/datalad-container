"""Support module for selecting a container from a dataset and its subdatasets.
"""

from datalad_container.containers_list import ContainersList

# Functions tried by find_container. These are called with the current dataset,
# the container name, and a dictionary mapping the container name to a record
# (as returned by containers-list).


def _get_the_one_and_only(_, name, containers):
    if name is None:
        if len(containers) == 1:
            # no questions asked, take container and run
            return list(containers.values())[0]
        else:
            raise ValueError("Must explicitly specify container"
                             " (known containers are: {})"
                             .format(', '.join(containers)))


def _get_container_by_name(_, name, containers):
    return containers.get(name)


def _get_container_by_path(ds, name, containers):
    from datalad.distribution.dataset import resolve_path
    container_path = resolve_path(name, ds)
    container = [c for c in containers.values()
                 if c['path'] == container_path]
    if len(container) == 1:
        return container[0]


# Entry point


def find_container(ds, container_name):
    """Find the container in dataset `ds` specified by `container_name`.

    Parameters
    ----------
    ds : Dataset
        Dataset to query.
    container_name : str or None
        Name in the form of how `containers-list -d ds -r` would report it
        (e.g., "s0/s1/cname").

    Returns
    -------
    The container record, as returned by containers-list.

    Raises
    ------
    ValueError if a uniquely matching container cannot be found.
    """
    recurse = container_name and "/" in container_name
    containers = {c['name']: c
                  for c in ContainersList.__call__(dataset=ds,
                                                   recursive=recurse)}

    if not containers:
        raise ValueError("No known containers. Use containers-add")

    fns = [
        _get_the_one_and_only,
        _get_container_by_name,
        _get_container_by_path,
    ]

    for fn in fns:
        container = fn(ds, container_name, containers)
        if container:
            return container

    raise ValueError(
        'Container selection impossible: not specified, ambiguous '
        'or unknown (known containers are: {})'
        .format(', '.join(containers))
    )
