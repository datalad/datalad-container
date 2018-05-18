
__docformat__ = 'restructuredtext'

import logging
import os.path as op

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod, EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.interface.utils import eval_results
from datalad.support.constraints import EnsureStr
from datalad.support.constraints import EnsureNone
from datalad.support.exceptions import InsufficientArgumentsError
from datalad.interface.results import get_status_dict

# required bound commands
from datalad.coreapi import save

from .definitions import definitions

lgr = logging.getLogger("datalad.containers.containers_add")


@build_doc
# all commands must be derived from Interface
class ContainersAdd(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Add a container to a dataset
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset to add the container to. If no dataset is
            given, an attempt is made to identify the dataset based on the
            current working directory""",
            constraints=EnsureDataset() | EnsureNone()
        ),
        name=Parameter(
            args=("name",),
            doc="""The name to register the container with. This simultanously
                determines the location within DATASET where to put that
                container""",
            metavar="NAME",
            constraints=EnsureStr(),
        ),
        url=Parameter(
            args=("-u", "--url"),
            doc="""An URL to get the container from. This alternatively can be
                read from config (datalad.containers.NAME.url). If both are
                available this parameter will take precedence""",
            metavar="URL",
            nargs="?",
            constraints=EnsureStr() | EnsureNone(),
        ),

        # TODO: The "prepared command stuff should ultimately go somewhere else
        # (probably datalad-run). But first figure out, how exactly to address
        # container datasets
        execute=Parameter(
            args=("-e", "--execute"),
            doc="""How to execute the container in case of a prepared command.
                For example this could read "singularity exec" or "docker run". If
                not set, a prepared command referencing this container will assume
                the container image itself to be the relevant executable""",
            metavar="EXEC",
            nargs="?",
            constraints=EnsureStr() | EnsureNone(),
        ),
        image=Parameter(
            args=("-i", "--image"),
            doc="""Path to the actual container image. This is relevant only in
                case the added container really is a dataset containing the
                image and is used to configure prepare commands in combination
                with EXEC""",
            metavar="IMAGE",
            nargs="?",
            constraints=EnsureStr() | EnsureNone(),

        )
    )

    @staticmethod
    @datasetmethod(name='containers_add')
    @eval_results
    def __call__(name, url=None, dataset=None, execute=None, image=None):
        if not name:
            raise InsufficientArgumentsError("`name` argument is required")

        ds = require_dataset(dataset, check_installed=True,
                             purpose='add container')

        # TODO inspecting a base location config is only needed when
        # no --image option is given
        loc_cfg_var = "datalad.containers.location"
        # TODO: We should provide an entry point (or sth similar) for extensions
        # to get config definitions into the ConfigManager. In other words an
        # easy way to extend definitions in datalad's common_cfgs.py.
        container_loc = \
            ds.config.obtain(
                loc_cfg_var,
                where=definitions[loc_cfg_var]['destination'],
                # if not False it would actually modify the
                # dataset config file -- undesirable
                store=False,
                default=definitions[loc_cfg_var]['default'],
                dialog_type=definitions[loc_cfg_var]['ui'][0],
                valtype=definitions[loc_cfg_var]['type'],
                **definitions[loc_cfg_var]['ui'][1]
            )

        result = get_status_dict(
            action="containers_add",
            path=op.join(ds.path, container_loc, name),
            type="file",
            logger=lgr,
        )

        if not url:
            url = ds.config.get("datalad.containers.{}.url".format(name))
        if not url:
            raise InsufficientArgumentsError(
                "URL is required and can be provided either via parameter "
                "'url' or config key 'datalad.containers.{}.url'"
                "".format(name))

        # collect bits for a final and single save() call
        to_save = []
        image_loc = op.join(container_loc, name)
        try:
            ds.repo.add_url_to_file(image_loc, url)
            to_save.append(image_loc)
            result["status"] = "ok"
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
        yield result
        # continue despite a remote access failure, the following config
        # setting will enable running the command again with just the name
        # given to ease a re-run

        # store configs
        ds.config.set("datalad.containers.{}.url".format(name), url)
        if execute:
            ds.config.add("datalad.containers.{}.exec".format(name), execute)
        if image:
            ds.config.add("datalad.containers.{}.image".format(name), image)
        # store changes
        to_save.append(op.join(".datalad", "config"))
        for r in ds.save(
                path=to_save,
                message="[DATALAD] Add containerized environment '{name}'".format(
                    name=name)):
            yield r
