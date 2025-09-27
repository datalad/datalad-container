"""
Importing this file extends datalad.support.external_version:

Adds:
    - external_versions["cmd:apptainer"]
    - external_versions["cmd:singularity"]
"""

from datalad.cmd import (
    StdOutErrCapture,
    WitlessRunner,
)
from datalad.support.external_versions import external_versions


def __get_apptainer_version():
    version = WitlessRunner().run("apptainer --version", protocol=StdOutErrCapture)['stdout'].strip()
    return version.split("apptainer version ")[1]


def __get_singularity_version():
    return WitlessRunner().run("singularity version", protocol=StdOutErrCapture)['stdout'].strip()


# Load external_versions and patch with "cmd:singularity" and "cmd:apptainer"
external_versions.add("cmd:apptainer", func=__get_apptainer_version)
external_versions.add("cmd:singularity", func=__get_singularity_version)
