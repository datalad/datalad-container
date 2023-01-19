#!/bin/sh
cd $(dirname "$(readlink -f "$0")")
(chmod -R +w ds;rm -rf ds) 2>/dev/null
set -x
datalad create ds
cd ds
mkdir containers
sudo apptainer build containers/alpine.sif docker://alpine
sudo apptainer overlay create --size 64 containers/overlay.img
sudo chown $USER:$USER containers/overlay.img
datalad -l debug containers-add alpine-with-overlay \
    --call-fmt 'apptainer exec --overlay {img_dir}/overlay.img {img} {cmd}' \
    --extra-inputs containers/overlay.img \
    -i containers/alpine.sif
datalad save
cat .datalad/config
datalad -l debug containers-run -n alpine-with-overlay 'uname -a > alpine-uname-a.txt'
cat alpine-uname-a.txt
