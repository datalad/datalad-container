"""Support module for selecting a container from a dataset and its subdatasets.
"""

import logging

from datalad.distribution.dataset import Dataset
from datalad.utils import Path

from datalad_container.containers_list import ContainersList

lgr = logging.getLogger("datalad_container.find_container")


def _list_containers(dataset, recursive, contains=None):
    return {c['name']: c
            for c in ContainersList.__call__(dataset=dataset,
                                             recursive=recursive,
                                             contains=contains,
                                             return_type='generator',
                                             on_failure='ignore',
                                             result_filter=None,
                                             result_renderer=None,
                                             result_xfm=None)}


def _get_subdataset_container(ds, container_name):
    """Try to get subdataset container matching `container_name`.

    This is the primary function tried by find_container_() when the container
    name looks like it is from a subdataset (i.e. has a slash).

    Parameters
    ----------
    ds : Dataset
    container_name : str

    Yields
    -------
    Result records for any installed subdatasets and a containers-list record
    for the container, if any, found for `container_name`.
    """
    name_parts = container_name.split('/')
    subds_names = name_parts[:-1]
    if Dataset(ds.pathobj / Path(*subds_names)).is_installed():
        # This avoids unnecessary work in the common case, but it can result in
        # not installing the necessary subdatasets in the rare case that chain
        # of submodule names point to a subdataset path that is installed while
        # the actual submodule paths contains uninstalled parts.
        lgr.debug(
            "Subdataset for %s is probably installed. Skipping install logic",
            container_name)
        return

    curds = ds
    for name in subds_names:
        for sub in curds.subdatasets(return_type='generator'):
            if sub['gitmodule_name'] == name:
                path = sub['path']
                yield from curds.get(
                    path, get_data=False,
                    on_failure='ignore', return_type='generator')
                curds = Dataset(path)
                break
        else:
            # There wasn't a submodule name chain that matched container_name.
            # Aside from an invalid name, the main case where this can happen
            # is when an image path is given for the container name.
            lgr.debug("Did not find submodule name %s in %s",
                      name, curds)
            return
    containers = _list_containers(dataset=ds, recursive=True,
                                  contains=curds.path)
    res = containers.get(container_name)
    if res:
        yield res


# Fallback functions tried by find_container_. These are called with the
# current dataset, the container name, and a dictionary mapping the container
# name to a record (as returned by containers-list).


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
    # Note: since datalad0.12.0rc6 resolve_path returns a Path object here,
    #       which then fails to equal c['path'] below as this is taken from
    #       config as a string
    container_path = str(resolve_path(name, ds))
    container = [c for c in containers.values()
                 if c['path'] == container_path]
    if len(container) == 1:
        return container[0]


# Entry points


def find_container_(ds, container_name=None):
    """Find the container in dataset `ds` specified by `container_name`.

    Parameters
    ----------
    ds : Dataset
        Dataset to query.
    container_name : str or None
        Name in the form of how `containers-list -d ds -r` would report it
        (e.g., "s0/s1/cname").

    Yields
    ------
    The container record, as returned by containers-list. Before that record,
    it may yield records of other action types, in particular "install" records
    for subdatasets that were installed to try to get access to a subdataset
    container.

    Raises
    ------
    ValueError if a uniquely matching container cannot be found.
    """
    recurse = container_name and "/" in container_name
    if recurse:
        for res in _get_subdataset_container(ds, container_name):
            # Before the container record, the results may include install
            # records. Don't relay "notneeded" results to avoid noise. Also,
            # don't propagate install failures, which may be due to an image
            # path being given or a non-existent container, both cases that are
            # handled downstream.
            if res.get("status") == "ok":
                yield res
            if res.get("action") == "containers":
                return

    containers = _list_containers(dataset=ds, recursive=recurse)
    if not containers:
        raise ValueError("No known containers. Use containers-add")

    fns = [
        _get_the_one_and_only,
        _get_container_by_name,
        _get_container_by_path,
    ]

    for fn in fns:
        lgr.debug("Trying to find container with %s", fn)
        container = fn(ds, container_name, containers)
        if container:
            yield container
            return

    raise ValueError(
        'Container selection impossible: not specified, ambiguous '
        'or unknown (known containers are: {})'
        .format(', '.join(containers))
    )


def find_container(ds, container_name=None):
    """Like `find_container_`, but just return the container record.
    """
    # Note: This function was once used directly by containers_run(), but that
    # now uses the find_container_() generator function directly. Now
    # find_container() exists for compatibility with third-party tools
    # (reproman) and the test_find.py tests.
    for res in find_container_(ds, container_name):
        if res.get("action") == "containers":
            return res
    raise RuntimeError(
        "bug: find_container_() should return container or raise exception")
