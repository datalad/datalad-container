"""Remove a container environment from a dataset"""

__docformat__ = 'restructuredtext'

import logging
import os.path as op

from datalad.distribution.dataset import (
    EnsureDataset,
    datasetmethod,
    require_dataset,
)
from datalad.interface.base import (
    Interface,
    build_doc,
    eval_results,
)
from datalad.interface.results import get_status_dict
from datalad.support.constraints import (
    EnsureNone,
    EnsureStr,
)
from datalad.support.param import Parameter
from datalad.utils import rmtree

from datalad_container.utils import get_container_configuration

lgr = logging.getLogger("datalad.containers.containers_remove")


@build_doc
# all commands must be derived from Interface
class ContainersRemove(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Remove a known container from a dataset

    This command is only removing a container from the committed
    Dataset configuration (configuration scope ``branch``). It will not
    modify any other configuration scopes.

    This command is *not* dropping the container image associated with the
    removed record, because it may still be needed for other dataset versions.
    In order to drop the container image, use the 'drop' command prior
    to removing the container configuration.
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset from removing a container. If no dataset
            is given, an attempt is made to identify the dataset based on the
            current working directory""",
            constraints=EnsureDataset() | EnsureNone()),
        name=Parameter(
            args=("name",),
            doc="""name of the container to remove""",
            metavar="NAME",
            constraints=EnsureStr(),
        ),
        remove_image=Parameter(
            args=("-i", "--remove-image",),
            doc="""if set, remove container image as well. Even with this flag,
            the container image content will not be dropped. Use the 'drop'
            command explicitly before removing the container configuration.""",
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

        container_cfg = get_container_configuration(ds, name)

        to_save = []
        if remove_image and 'image' in container_cfg:
            imagepath = ds.pathobj / container_cfg['image']
            # we use rmtree() and not .unlink(), because
            # the image could be more than a single file underneath
            # this location (e.g., docker image dumps)
            rmtree(imagepath)
            # at the very end, save() will take care of committing
            # any removal that just occurred
            to_save.append(imagepath)

        if container_cfg:
            ds.config.remove_section(
                f'datalad.containers.{name}',
                scope='branch',
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
