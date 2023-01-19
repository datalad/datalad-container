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
sudo apptainer overlay create --size 64 containers/overlay2.img
sudo chown $USER:$USER containers/overlay2.img
datalad $@ containers-add alpine -i containers/alpine.sif
datalad $@ containers-add alpine-with-overlay \
    --call-fmt 'apptainer exec --overlay {img_dir}/overlay.img {img} {cmd}' \
    --extra-inputs containers/overlay.img \
    -i containers/alpine.sif
datalad $@ containers-add alpine-with-two-overlays \
    --call-fmt 'apptainer exec --overlay {img_dir}/overlay.img --overlay {img_dir}/overlay2.img:ro {img} {cmd}' \
    --extra-inputs containers/overlay.img containers/overlay2.img \
    -i containers/alpine.sif
datalad save
echo 1 > file.txt
datalad save
cat .datalad/config
datalad $@ containers-run -n alpine -o alpine-uname-a.txt 'uname -a > {outputs[0]}'
cat alpine-uname-a.txt
datalad $@ containers-run -n alpine-with-overlay -o alpine-with-overlay-uname-a.txt 'uname -a > {outputs[0]}'
cat alpine-with-overlay-uname-a.txt
datalad $@ containers-run -n alpine-with-two-overlays -o alpine-with-two-overlays-uname-a.txt 'uname -a > {outputs[0]}'
cat alpine-with-two-overlays-uname-a.txt
