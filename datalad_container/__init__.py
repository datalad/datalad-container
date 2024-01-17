"""DataLad container extension"""

__docformat__ = 'restructuredtext'

# Imported to set singularity/apptainer version commands at init
import datalad_container.extractors._load_singularity_versions  # noqa

# defines a datalad command suite
# this symbold must be identified as a setuptools entrypoint
# to be found by datalad
command_suite = (
    # description of the command suite, displayed in cmdline help
    "Containerized environments",
    [
        # specification of a command, any number of commands can be defined
        (
            # importable module that contains the command implementation
            'datalad_container.containers_list',
            # name of the command class implementation in above module
            'ContainersList',
            'containers-list',
            'containers_list',
        ),
        (
            'datalad_container.containers_remove',
            # name of the command class implementation in above module
            'ContainersRemove',
            'containers-remove',
            'containers_remove',

        ),
        (
            'datalad_container.containers_add',
            # name of the command class implementation in above module
            'ContainersAdd',
            'containers-add',
            'containers_add',

        ),
        (
            'datalad_container.containers_run',
            'ContainersRun',
            'containers-run',
            'containers_run',

        )
    ]
)

from os.path import join as opj

from datalad.support.constraints import EnsureStr
from datalad.support.extensions import register_config

register_config(
    'datalad.containers.location',
    'Container location',
    description='path within the dataset where to store containers',
    type=EnsureStr(),
    default=opj(".datalad", "environments"),
    dialog='question',
    scope='dataset',
)

from . import _version

__version__ = _version.get_versions()['version']
