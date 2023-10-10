"""Drop-in replacement for `datalad run` for command execution in a container"""

__docformat__ = 'restructuredtext'

import logging
import os.path as op
from pathlib import Path
import sys

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.exceptions import CapturedException
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod
from datalad.distribution.dataset import require_dataset
from datalad.interface.base import eval_results
from datalad.utils import ensure_iter

from datalad.interface.results import get_status_dict
from datalad.core.local.run import (
    Run,
    get_command_pwds,
    normalize_command,
    run_command,
)
from datalad_container.find_container import find_container_

lgr = logging.getLogger("datalad.containers.containers_run")

# Environment variable to be set during execution to possibly
# inform underlying shim scripts about the original name of
# the container
CONTAINER_NAME_ENVVAR = 'DATALAD_CONTAINER_NAME'

_run_params = dict(
    Run._params_,
    container_name=Parameter(
        args=('-n', '--container-name',),
        metavar="NAME",
        doc="""Specify the name of or a path to a known container to use 
        for execution, in case multiple containers are configured."""),
)


@build_doc
# all commands must be derived from Interface
class ContainersRun(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Drop-in replacement of 'run' to perform containerized command execution

    Container(s) need to be configured beforehand (see containers-add). If no
    container is specified and only one container is configured in the current
    dataset, it will be selected automatically. If more than one container is
    registered in the current dataset or to access containers from subdatasets,
    the container has to be specified.

    A command is generated based on the input arguments such that the
    container image itself will be recorded as an input dependency of
    the command execution in the `run` record in the git history.

    During execution the environment variable {name_envvar} is set to the
    name of the used container.
    """

    _docs_ = dict(
        name_envvar=CONTAINER_NAME_ENVVAR
    )

    _params_ = _run_params

    # Analogous to 'run' command - stop on first error
    on_failure = 'stop'

    @staticmethod
    @datasetmethod(name='containers_run')
    @eval_results
    def __call__(cmd, container_name=None, dataset=None,
                 inputs=None, outputs=None, message=None, expand=None,
                 explicit=False, sidecar=None):
        from unittest.mock import patch  # delayed, since takes long (~600ms for yoh)
        pwd, _ = get_command_pwds(dataset)
        ds = require_dataset(dataset, check_installed=True,
                             purpose='run a containerized command execution')

        container = None
        for res in find_container_(ds, container_name):
            if res.get("action") == "containers":
                container = res
            else:
                yield res
        assert container, "bug: container should always be defined here"

        image_path = op.relpath(container["path"], pwd)
        # container record would contain path to the (sub)dataset containing
        # it.  If not - take current dataset, as it must be coming from it
        image_dspath = op.relpath(container.get('parentds', ds.path), pwd)

        # sure we could check whether the container image is present,
        # but it might live in a subdataset that isn't even installed yet
        # let's leave all this business to `get` that is called by `run`

        cmd = normalize_command(cmd)
        # expand the command with container execution
        if 'cmdexec' in container:
            callspec = container['cmdexec']

            # Temporary kludge to give a more helpful message
            if callspec.startswith("["):
                import json
                try:
                    json.loads(callspec)
                except json.JSONDecodeError:
                    pass  # Never mind, false positive.
                else:
                    raise ValueError(
                        'cmdexe {!r} is in an old, unsupported format. '
                        'Convert it to a plain string.'.format(callspec))
            try:
                cmd_kwargs = dict(
                    # point to the python installation that runs *this* code
                    # we know that it would have things like the docker
                    # adaptor installed with this extension package
                    python=sys.executable,
                    img=image_path,
                    cmd=cmd,
                    img_dspath=image_dspath,
                    img_dirpath=op.dirname(image_path) or ".",
                )
                cmd = callspec.format(**cmd_kwargs)
            except KeyError as exc:
                yield get_status_dict(
                    'run',
                    ds=ds,
                    status='error',
                    message=(
                        'Unrecognized cmdexec placeholder: %s. '
                        'See containers-add for information on known ones: %s',
                        exc,
                        ", ".join(cmd_kwargs)))
                return
        else:
            # just prepend and pray
            cmd = container['path'] + ' ' + cmd

        extra_inputs = []
        for extra_input in ensure_iter(container.get("extra-input",[]), set):
            try:
                xi_kwargs = dict(
                    img_dspath=image_dspath,
                    img_dirpath=op.dirname(image_path) or ".",
                )
                extra_inputs.append(extra_input.format(**xi_kwargs))
            except KeyError as exc:
                yield get_status_dict(
                    'run',
                    ds=ds,
                    status='error',
                    message=(
                        'Unrecognized extra_input placeholder: %s. '
                        'See containers-add for information on known ones: %s',
                        exc,
                        ", ".join(xi_kwargs)))
                return

        lgr.debug("extra_inputs = %r", extra_inputs)

        if '-m datalad_container.adapters.docker run' in cmd:
            # this will use the docker adapter to execute the container.
            # below we let the adaptor have a first look at the image
            # it will run. The adaptor might query a local docker service,
            # and try to populate missing image parts -- possibly avoiding
            # a download (via the `get()` that `run()` would perform), whenever
            # the local service already has the respective images.
            # this is a scenario that would occur frequently in short-lived
            # clones that are repeatedly generated on the same machine.
            from datalad_container.adapters.docker import repopulate_from_daemon
            contds = require_dataset(
                container['parentds'], check_installed=True,
                purpose='check for docker images')
            try:
                repopulate_from_daemon(
                    contds,
                    # we use the container report here too, and not any of the
                    # processed variants from above to stay internally
                    # consistent
                    imgpath=Path(container['path']),
                )
            except Exception as e:
                # get basic logging of a failure, but overall consider this
                # a "best effort". if anything fails, we will silently fall
                # back on a standard "get" via the `extra_inputs` below
                CapturedException(e)

        with patch.dict('os.environ',
                        {CONTAINER_NAME_ENVVAR: container['name']}):
            # fire!
            for r in run_command(
                    cmd=cmd,
                    dataset=dataset or (ds if ds.path == pwd else None),
                    inputs=inputs,
                    extra_inputs=[image_path] + extra_inputs,
                    outputs=outputs,
                    message=message,
                    expand=expand,
                    explicit=explicit,
                    sidecar=sidecar):
                yield r
