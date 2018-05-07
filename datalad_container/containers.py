import logging
from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod, EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.interface.utils import eval_results
from datalad.support.constraints import EnsureChoice, EnsureNone, EnsureStr
from datalad.interface.results import get_status_dict


lgr = logging.getLogger("datalad.containers.containers")


def _list_containers(dataset):

    from os import listdir
    import os.path as op

    container_loc = op.join(dataset.path,
                            dataset.config.get("datalad.containers.location")
                            )

    for r in [n for n in listdir(container_loc) if not n.startswith(".")]:
        yield {'status': 'ok',
               'path': op.join(dataset.path, container_loc, r),
               'type': '', # ??
               'name': r, # ????? message instead?
               }


def _add_container():
    raise NotImplementedError


def _configure_container():
    raise NotImplementedError


@build_doc
# all commands must be derived from Interface
class Containers(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Short description of the command

    Long description of arbitrary volume.
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset to configure/query.  If
        no dataset is given, an attempt is made to identify the dataset
        based on the input and/or the current working directory""",
            constraints=EnsureDataset() | EnsureNone()),
        action=Parameter(
            args=('action',),
            nargs='?',
            metavar='ACTION',
            doc="""command action selection (see general documentation)""",

                # TODO: Remove? What else?
            constraints=EnsureChoice('list', 'add', 'configure') | EnsureNone()),
        name=Parameter(
            args=('-n', '--name',),
            metavar='NAME',
            doc="""name of the container""",
            constraints=EnsureStr() | EnsureNone()),
        url=Parameter(
            args=('--url',),
            metavar='URL',
            doc="""url to get the container image from""",
            constraints=EnsureStr() | EnsureNone(),
            nargs="?"),
    )

    @staticmethod
    @datasetmethod(name='containers')
    @eval_results
    def __call__(dataset=None, action='list', name=None, url=None):

        ds = require_dataset(dataset, check_installed=True,
                             purpose='container configuration')

        action_worker_map = {
            'list': _list_containers,
            'add': _add_container,
            'configure': _configure_container,
        }

        try:
            worker = action_worker_map[action]
        except KeyError:
            # TODO: raise InvalidArgument
            pass

        # TODO:figure configs we'll need:

        "datalad.containers.NAME.url"    # ? Actually not needed. File => annex, Dataset => submodule
        "datalad.containers.NAME.exec"
        "datalad.containers.NAME.image"  # Only relevant for datasets; Another way? AnnotatePaths?

        # "prepared commands"?
        # => Not of concern for containers-extension
