"""Add a container environment to a dataset"""

__docformat__ = 'restructuredtext'

import re
import logging
import os.path as op
from simplejson import dumps
from argparse import REMAINDER

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
from datalad.support.network import get_local_file_url

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
            doc="""The name to register the container under. This also
                determines the default location of the container image
                within the dataset.""",
            metavar="NAME",
            constraints=EnsureStr(),
        ),
        url=Parameter(
            args=("-u", "--url"),
            doc="""A URL (or local path) to get the container image from""",
            metavar="URL",
            constraints=EnsureStr() | EnsureNone(),
        ),

        # TODO: The "prepared command stuff should ultimately go somewhere else
        # (probably datalad-run). But first figure out, how exactly to address
        # container datasets
        call_fmt=Parameter(
            args=("--call-fmt",),
            doc="""Command format string indicating how to execute a command in
            this container, e.g. "singularity exec {img} {cmd}". Where '{img}'
            is a placeholder for the path to the container image and '{cmd}' is
            replaced with the desired command. [CMD: Note: This option should
            be given at the end because all remaining arguments are consumed as
            its value. CMD]""",
            metavar="FORMAT",
            nargs=REMAINDER,
            constraints=EnsureStr() | EnsureNone(),
        ),
        image=Parameter(
            args=("-i", "--image"),
            doc="""Relative path of the container image within the dataset. If not
                given, a default location will be determined using the
                `name` argument.""",
            metavar="IMAGE",
            constraints=EnsureStr() | EnsureNone(),

        )
    )

    @staticmethod
    @datasetmethod(name='containers_add')
    @eval_results
    def __call__(name, url=None, dataset=None, call_fmt=None, image=None):
        if not name:
            raise InsufficientArgumentsError("`name` argument is required")

        ds = require_dataset(dataset, check_installed=True,
                             purpose='add container')

        # prevent madness in the config file
        if not re.match(r'^[0-9a-zA-Z-]+$', name):
            raise ValueError(
                "Container names can only contain alphanumeric characters "
                "and '-', got: '{}'".format(name))

        if not image:
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
            image = op.join(ds.path, container_loc, name, 'image')
        else:
            image = op.join(ds.path, image)

        result = get_status_dict(
            action="containers_add",
            path=image,
            type="file",
            logger=lgr,
        )

        # collect bits for a final and single save() call
        to_save = []
        if url:
            if op.exists(url):
                # annex wants a real url
                url = get_local_file_url(url)
            try:
                ds.repo.add_url_to_file(image, url)
            except Exception as e:
                result["status"] = "error"
                result["message"] = str(e)
                yield result
            # TODO do we have to take care of making the image executable
            # if --call_fmt is not provided?
            to_save.append(image)
        # continue despite a remote access failure, the following config
        # setting will enable running the command again with just the name
        # given to ease a re-run
        if not op.lexists(image):
            result["status"] = "error"
            result["message"] = ('no image at %s', image)
            yield result
            return

        # store configs
        cfgbasevar = "datalad.containers.{}".format(name)
        # force store the image, and prevent multiple entries
        ds.config.set(
            "{}.image".format(cfgbasevar),
            op.relpath(image, start=ds.path),
            force=True)
        if call_fmt:
            ds.config.set(
                "{}.cmdexec".format(cfgbasevar),
                dumps(call_fmt),
                force=True)
        # store changes
        to_save.append(op.join(".datalad", "config"))
        for r in ds.save(
                path=to_save,
                message="[DATALAD] Configure containerized environment '{name}'".format(
                    name=name)):
            yield r
        result["status"] = "ok"
        yield result
