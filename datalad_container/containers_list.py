
__docformat__ = 'restructuredtext'

import logging
from os import listdir
import os.path as op

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod, EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.interface.utils import eval_results
from datalad.support.constraints import EnsureChoice, EnsureNone, EnsureStr
from datalad.interface.results import get_status_dict
from datalad.interface.annotate_paths import AnnotatePaths
from datalad.interface.annotate_paths import annotated2content_by_ds

from .definitions import definitions

lgr = logging.getLogger("datalad.containers.containers_list")


@build_doc
# all commands must be derived from Interface
class ContainersList(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """List containers known to a dataset
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset to query. If no dataset is given, an 
            attempt is made to identify the dataset based on the current working
             directory""",
            constraints=EnsureDataset() | EnsureNone()),
    )

    @staticmethod
    @datasetmethod(name='containers_list')
    @eval_results
    def __call__(dataset=None):

        ds = require_dataset(dataset, check_installed=True,
                             purpose='list containers')

        loc_cfg_var = "datalad.containers.location"

        # TODO: We should provide an entry point (or sth similar) for extensions
        # to get config definitions into the ConfigManager. In other words an
        # easy way to extend definitions in datalad's common_cfgs.py.
        container_loc = \
            ds.config.obtain(loc_cfg_var,
                             where=definitions[loc_cfg_var]['destination'],
                             store=True,
                             default=definitions[loc_cfg_var]['default'],
                             dialog_type=definitions[loc_cfg_var]['ui'][0],
                             valtype=definitions[loc_cfg_var]['type'],
                             **definitions[loc_cfg_var]['ui'][1]
                             )

        from six import PY3

        try:
            location_content = listdir(op.join(ds.path, container_loc))
        except FileNotFoundError if PY3 else (OSError, IOError) as e:
            # TODO: Right now, just retunr nothing, since there is nothing
            # But may also be an "impossible" result, since the configured
            # common mountpoint isn't existing (needs "e.errno == errno.ENOENT"
            # in addition in PY2)
            return

        for r in [n for n in location_content if not n.startswith(".")]:
            yield {'status': 'ok',
                   'action': 'containers_list',
                   'path': op.join(ds.path, container_loc, r),
                   # TODO: Might be an image file or a dataset.
                   # Use AnnotatePath with container_loc?
                   'type': 'file',
                   'name': r,
                   }

        # See comment about AnnotatePath
        # for ap in AnnotatePaths.__call__(
        #         path=op.join(ds.path, container_loc),
        #         dataset=ds,
        #         recursive=True,  # TODO: Do we want that optional?
        #         recursion_limit=None,  # TODO: See above
        #         action='list containers',
        #         unavailable_path_status='',
        #         nondataset_path_status='impossible',
        #         return_type='generator',
        #         on_failure='ignore'):

        # TODO: result_renderer? We prob. want to show the names instead of
        # actual paths
