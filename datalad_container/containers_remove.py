"""Remove a container environment from a dataset"""

__docformat__ = 'restructuredtext'

import logging
import os.path as op

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod, EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.interface.utils import eval_results
from datalad.support.constraints import EnsureNone
from datalad.support.constraints import EnsureStr
from datalad.interface.results import get_status_dict

# required bound methods
from datalad.coreapi import save
from datalad.coreapi import remove


lgr = logging.getLogger("datalad.containers.containers_remove")


@build_doc
# all commands must be derived from Interface
class ContainersRemove(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Remove a known container from a dataset
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset to query. If no dataset is given, an
            attempt is made to identify the dataset based on the current
            working directory""",
            constraints=EnsureDataset() | EnsureNone()),
        name=Parameter(
            args=("name",),
            doc="""name of the container to remove""",
            metavar="NAME",
            constraints=EnsureStr(),
        ),
        remove_image=Parameter(
            args=("-i", "--remove-image",),
            doc="""if set, remove container image as well""",
            action="store_true",
        ),
    )

    @staticmethod
    @datasetmethod(name='containers_remove')
    @eval_results
    def __call__(name, dataset=None, remove_image=False):
        ds = require_dataset(dataset, check_installed=True,
                             purpose='remove a container')

        res = get_status_dict(
            ds=ds,
            action='containers_remove',
            logger=lgr)

        section = 'datalad.containers.{}'.format(name)
        imagecfg = '{}.image'.format(section)

        to_save = []
        if remove_image and imagecfg in ds.config:
            imagepath = ds.config.get(imagecfg)
            if op.lexists(op.join(ds.path, imagepath)):
                for r in ds.remove(
                        path=imagepath,
                        # XXX shortcomming: this is the only way to say:
                        # don't drop
                        check=False,
                        # config setting might be outdated and image no longer
                        # there -> no reason to fail, just report
                        on_failure='ignore',
                        save=False):
                    yield r
                to_save.append(imagepath)

        if section in ds.config.sections():
            ds.config.remove_section(
                section,
                where='dataset',
                reload=True)
            res['status'] = 'ok'
            to_save.append(op.join('.datalad', 'config'))
        else:
            res['status'] = 'notneeded'
        if to_save:
            for r in ds.save(
                    path=to_save,
                    message='[DATALAD] Remove container {}'.format(name)):
                yield r
        yield res
