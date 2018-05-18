"""DataLad container extension"""

__docformat__ = 'restructuredtext'

from .version import __version__

# defines a datalad command suite
# this symbold must be indentified as a setuptools entrypoint
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
