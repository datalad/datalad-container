"""Add a container environment to a dataset"""

__docformat__ = 'restructuredtext'

import json
import logging
import os
import os.path as op
import re
import sys
from shutil import copyfile

from datalad.cmd import WitlessRunner
from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.support.param import Parameter
from datalad.distribution.dataset import datasetmethod, EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.interface.base import eval_results
from datalad.support.constraints import EnsureStr
from datalad.support.constraints import EnsureNone
from datalad.support.exceptions import InsufficientArgumentsError
from datalad.interface.results import get_status_dict

from .definitions import definitions

lgr = logging.getLogger("datalad.containers.containers_add")

# The DataLad special remote has built-in support for Singularity Hub URLs. Let
# it handle shub:// URLs if it's available.
_HAS_SHUB_DOWNLOADER = True
try:
    import datalad.downloaders.shub
except ImportError:
    lgr.debug("DataLad's shub downloader not found. "
              "Custom handling for shub:// will be used")
    _HAS_SHUB_DOWNLOADER = False


def _resolve_img_url(url):
    """Takes a URL and tries to resolve it to an actual download
    URL that `annex addurl` can handle"""
    if not _HAS_SHUB_DOWNLOADER and url.startswith('shub://'):
        # TODO: Remove this handling once the minimum DataLad version is at
        # least 0.14.
        lgr.debug('Query singularity-hub for image download URL')
        import requests
        req = requests.get(
            'https://www.singularity-hub.org/api/container/{}'.format(
                url[7:]))
        shub_info = json.loads(req.text)
        url = shub_info['image']
    return url


def _guess_call_fmt(ds, name, url):
    """Helper to guess a container exec setup based on
    - a name (to be able to look up more config
    - a plain url to make inference based on the source location

    Should return `None` is no guess can be made.
    """
    if url is None:
        return None
    elif url.startswith('shub://') or url.startswith('docker://'):
        return 'singularity exec {img} {cmd}'
    elif url.startswith('dhub://'):
        return op.basename(sys.executable) + ' -m datalad_container.adapters.docker run {img} {cmd}'


def _ensure_datalad_remote(repo):
    """Initialize and enable datalad special remote if it isn't already."""
    dl_remote = None
    for info in repo.get_special_remotes().values():
        if info.get("externaltype") == "datalad":
            dl_remote = info["name"]
            break

    if not dl_remote:
        from datalad.consts import DATALAD_SPECIAL_REMOTE
        from datalad.customremotes.base import init_datalad_remote

        init_datalad_remote(repo, DATALAD_SPECIAL_REMOTE, autoenable=True)
    elif repo.is_special_annex_remote(dl_remote, check_if_known=False):
        lgr.debug("datalad special remote '%s' is already enabled",
                  dl_remote)
    else:
        lgr.debug("datalad special remote '%s' found. Enabling",
                  dl_remote)
        repo.enable_remote(dl_remote)


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
            doc="""A URL (or local path) to get the container image from. If
            the URL scheme is one recognized by Singularity ('shub://' or
            'docker://'), a command format string for Singularity-based
            execution will be auto-configured when
            [CMD: --call-fmt CMD][PY: call_fmt PY] is not specified.
            For Docker-based container execution with the URL scheme 'dhub://',
            the rest of the URL will be interpreted as the argument to
            'docker pull', the image will be saved to a location
            specified by `name`, and the call format will be auto-configured
            to run docker, unless overwritten.""",
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
            replaced with the desired command. Additional placeholders:
            '{img_dspath}' is relative path to the dataset containing the image.
            """,
            metavar="FORMAT",
            constraints=EnsureStr() | EnsureNone(),
        ),
        image=Parameter(
            args=("-i", "--image"),
            doc="""Relative path of the container image within the dataset. If not
                given, a default location will be determined using the
                `name` argument.""",
            metavar="IMAGE",
            constraints=EnsureStr() | EnsureNone(),

        ),
        update=Parameter(
            args=("--update",),
            action="store_true",
            doc="""Update the existing container for `name`. If no other
            options are specified, URL will be set to 'updateurl', if
            configured. If a container with `name` does not already exist, this
            option is ignored."""
        )
    )

    @staticmethod
    @datasetmethod(name='containers_add')
    @eval_results
    def __call__(name, url=None, dataset=None, call_fmt=None, image=None,
                 update=False):
        if not name:
            raise InsufficientArgumentsError("`name` argument is required")

        ds = require_dataset(dataset, check_installed=True,
                             purpose='add container')
        runner = WitlessRunner()

        # prevent madness in the config file
        if not re.match(r'^[0-9a-zA-Z-]+$', name):
            raise ValueError(
                "Container names can only contain alphanumeric characters "
                "and '-', got: '{}'".format(name))

        cfgbasevar = "datalad.containers.{}".format(name)
        if cfgbasevar + ".image" in ds.config:
            if not update:
                yield get_status_dict(
                    action="containers_add", ds=ds, logger=lgr,
                    status="impossible",
                    message=("Container named %r already exists. "
                             "Use --update to reconfigure.",
                             name))
                return

            if not (url or image or call_fmt):
                # No updated values were provided. See if an update url is
                # configured (currently relevant only for Singularity Hub).
                url = ds.config.get(cfgbasevar + ".updateurl")
                if not url:
                    yield get_status_dict(
                        action="containers_add", ds=ds, logger=lgr,
                        status="impossible",
                        message="No values to update specified")
                    return

            call_fmt = call_fmt or ds.config.get(cfgbasevar + ".cmdexec")
            image = image or ds.config.get(cfgbasevar + ".image")

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

        if call_fmt is None:
            # maybe built in knowledge can help
            call_fmt = _guess_call_fmt(ds, name, url)

        # collect bits for a final and single save() call
        to_save = []
        imgurl = url
        was_updated = False
        if url:
            if update and op.lexists(image):
                was_updated = True
                # XXX: check=False is used to avoid dropping the image. It
                # should use drop=False if remove() gets such an option (see
                # DataLad's gh-2673).
                for r in ds.remove(image, save=False, check=False,
                                   return_type="generator"):
                    yield r

            imgurl = _resolve_img_url(url)
            lgr.debug('Attempt to obtain container image from: %s', imgurl)
            if url.startswith("dhub://"):
                from .adapters import docker

                docker_image = url[len("dhub://"):]

                lgr.debug(
                    "Running 'docker pull %s and saving image to %s",
                    docker_image, image)
                runner.run(["docker", "pull", docker_image])
                docker.save(docker_image, image)
            elif url.startswith("docker://"):
                image_dir, image_basename = op.split(image)
                if not image_basename:
                    raise ValueError("No basename in path {}".format(image))
                if image_dir and not op.exists(image_dir):
                    os.makedirs(image_dir)

                lgr.info("Building Singularity image for %s "
                         "(this may take some time)",
                         url)
                runner.run(["singularity", "build", image_basename, url],
                           cwd=image_dir or None)
            elif op.exists(url):
                lgr.info("Copying local file %s to %s", url, image)
                image_dir = op.dirname(image)
                if image_dir and not op.exists(image_dir):
                    os.makedirs(image_dir)
                copyfile(url, image)
            else:
                if _HAS_SHUB_DOWNLOADER and url.startswith('shub://'):
                    _ensure_datalad_remote(ds.repo)

                try:
                    ds.repo.add_url_to_file(image, imgurl)
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
        if imgurl != url:
            # store originally given URL, as it resolves to something
            # different and maybe can be used to update the container
            # at a later point in time
            ds.config.set("{}.updateurl".format(cfgbasevar), url)
        # force store the image, and prevent multiple entries
        ds.config.set(
            "{}.image".format(cfgbasevar),
            op.relpath(image, start=ds.path),
            force=True)
        if call_fmt:
            ds.config.set(
                "{}.cmdexec".format(cfgbasevar),
                call_fmt,
                force=True)
        # store changes
        to_save.append(op.join(".datalad", "config"))
        for r in ds.save(
                path=to_save,
                message="[DATALAD] {do} containerized environment '{name}'".format(
                    do="Update" if was_updated else "Configure",
                    name=name)):
            yield r
        result["status"] = "ok"
        yield result
