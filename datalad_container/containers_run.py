"""Drop-in replacement for `datalad run` for command execution in a container"""

__docformat__ = 'restructuredtext'

import logging
import os.path as op
from simplejson import loads

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod
from datalad.distribution.dataset import require_dataset
from datalad.interface.utils import eval_results

from datalad.interface.run import Run
from datalad.interface.run import get_command_pwds
from datalad_container.containers_list import ContainersList

lgr = logging.getLogger("datalad.containers.containers_run")


_run_params = dict(
    Run._params_,
    container_name=Parameter(
        args=('-n', '--container-name',),
        metavar="NAME",
        doc="""Specify the name of a known container to use for execution,
        in case multiple containers are configured."""),
)


@build_doc
# all commands must be derived from Interface
class ContainersRun(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Drop-in replacement of 'run' to perform containerized command execution

    Container(s) need to be configured beforehand (see containers-add).
    If only one container is known, it will be selected automatically,
    otherwise a specific container has to be specified.

    A command is generated based on the input arguments such that the
    container image itself will be recorded as an input dependency of
    the command execution in the `run` record in the git history.
    """

    _params_ = _run_params

    @staticmethod
    @datasetmethod(name='containers_run')
    @eval_results
    def __call__(cmd, container_name=None, dataset=None,
                 inputs=None, outputs=None, message=None, expand=None):
        pwd, _ = get_command_pwds(dataset)
        ds = require_dataset(dataset, check_installed=True,
                             purpose='run a containerized command execution')

        # get the container list
        containers = {c['name']: c
                      for c in ContainersList.__call__(dataset=ds)}

        if container_name is None and len(containers) == 1:
            # no questions asked, take container and run
            container = containers.popitem()[1]
        elif container_name and container_name in containers:
            container = containers[container_name]
        else:
            # anything else is an error
            raise ValueError(
                'Container selection impossible: not specified or unknown '
                '(known containers are: {})'.format(list(containers.keys())))

        image_path = op.relpath(container["path"], pwd)

        # sure we could check whether the container image is present,
        # but it might live in a subdataset that isn't even installed yet
        # let's leave all this business to `get` that is called by `run`

        # expand the command with container execution
        if 'cmdexec' in container:
            callspec = loads(container['cmdexec'])
            fullcmd = []
            for c in callspec:
                if c == '{cmd}':
                    fullcmd.extend(cmd)
                elif c == '{img}':
                    fullcmd.append(image_path)
                else:
                    fullcmd.append(c)
            cmd = fullcmd
        else:
            # just prepend and pray
            cmd = [container['path']] + cmd

        # with amend inputs to also include the container image
        inputs = (inputs or []) + [image_path]

        # fire!
        for r in Run.__call__(
                cmd=cmd,
                dataset=ds,
                inputs=inputs,
                outputs=outputs,
                message=message,
                expand=expand,
                on_failure="ignore"):
            yield r
