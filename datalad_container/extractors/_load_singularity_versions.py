"""
Importing this file extends datalad.support.external_version:

Adds:
    - external_versions["cmd:apptainer"]
    - external_versions["cmd:singularity"]
"""
import subprocess

from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.support.external_versions import external_versions


def __get_apptainer_version():
    version = WitlessRunner().run("apptainer --version", protocol=StdOutCapture)['stdout'].strip()
    return version.split("apptainer version ")[1]


def __get_singularity_version():
    return WitlessRunner().run("singularity version", protocol=StdOutCapture)['stdout'].strip()


# Load external_versions and patch with "cmd:singularity" and "cmd:apptainer"
external_versions.add("cmd:apptainer", func=__get_apptainer_version)
external_versions.add("cmd:singularity", func=__get_singularity_version)
