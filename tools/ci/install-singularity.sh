#!/bin/bash
set -ex -o pipefail
release="$(curl -fsSL https://api.github.com/repos/sylabs/singularity/releases/latest | jq -r .tag_name)"
codename="$(lsb_release -cs)"
arch="$(dpkg --print-architecture)"
wget -O /tmp/singularity-ce.deb https://github.com/sylabs/singularity/releases/download/$release/singularity-ce_${release#v}-${codename}_$arch.deb
set -x
sudo apt-get install uidmap
sudo dpkg -i /tmp/singularity-ce.deb
sudo apt-get install -f
