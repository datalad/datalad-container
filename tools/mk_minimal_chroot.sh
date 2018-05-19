#!/bin/bash
#
# bootstrap a tiny chroot (26MB compressed)
#
# run with sudo

set -e -u

chrootdir=$(mktemp -d)
echo "Working in $chrootdir"
debootstrap --variant=minbase --no-check-gpg stretch "$chrootdir"
find "$chrootdir"/var/cache/apt/archives -type f -delete
find "$chrootdir"/var/lib/apt/lists/ -type f -delete
rm -rf "$chrootdir"/usr/share/doc/*
rm -rf "$chrootdir"/usr/share/man
tar --show-transformed-names --transform=s,^.*$(basename $chrootdir),minichroot, -cvjf minichroot.tar.xz "$chrootdir"
echo "chroot tarball at minichroot.tar.xz"
