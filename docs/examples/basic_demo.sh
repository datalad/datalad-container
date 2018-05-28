#!/bin/sh
# SKIP_IN_V6

set -e

OLD_PWD=$PWD

# BOILERPLATE

#% EXAMPLE START
#
# Getting started
# ***************
#
# The Datalad container extension provides a few commands to register
# containers with a dataset and use them for execution of arbitray
# commands. In order to get going quickly, we only need a dataset
# and a ready-made container. For this demo we will start with a
# fresh dataset and a demo container from Singularity-Hub.
#%

# fresh dataset
datalad create demo
cd demo

# register container straight from Singularity-Hub
datalad containers-add my1st --url shub://datalad/datalad-container:testhelper

#%
# This will download the container image, add it to the dataset, and record
# basic information on the container under its name "my1st" in the dataset's
# configuration at ``.datalad/config``.
#
# Now we are all set to use this container for command execution. All it needs
# is to swap the command `datalad run` with `datalad containers-run`. The
# command is automatically executed in the registered container and the results
# (if there are any) will be added to the dataset:
#%

datalad containers-run cp /etc/debian_version proof.txt

#%
# If there is more than one container registered, the desired container needs
# to be specifed via the ``--name`` option. Containers do not need to come from
# Singularity-Hub, but can be local images too. Via the ``containers-add
# --call-fmt`` option it is possible to configure how exactly a container
# is being executed, or which local directories shall be made available to
# a container.
#
# At the moment there is built-in support for Singularity images, but other
# container execution systems can be used together with custom helper scripts.
# Direct support for Docker is under development.
#% EXAMPLE END

testEquality() {
  assertEquals 1 1
}

cd "$OLD_PWD"
[ -n "$DATALAD_TESTS_RUNCMDLINE" ] && . shunit2 || true
