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
    strip_str = len("apptainer version ")
    return version[strip_str:]


def __get_singularity_version():
    version = WitlessRunner().run("singularity version", protocol=StdOutCapture)['stdout'].strip()

    # It may be possible to have both apptainer and singularity installed.
    # If singularity is installed independently, the versions will not match.
    apptainer_version = external_versions["cmd:apptainer"]
    if apptainer_version and apptainer_version == version:
        return None
    return version

# Load external_versions and patch with "cmd:singularity" and "cmd:apptainer"
external_versions.add("cmd:apptainer", func=__get_apptainer_version)
external_versions.add("cmd:singularity", func=__get_singularity_version)
