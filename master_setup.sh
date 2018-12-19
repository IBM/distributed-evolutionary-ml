#!/bin/bash

# Copyright (C) IBM Corporation 2018
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This Bash script can be used to configure the master node, on which you will run `master.py`
# You can run this file as a regular user, in which case it may ask you for `sudo` access.
# This script will install the python dependencies as a regular user, and set-up things as root only when
# necessary.

# Install docker, sshpass, pixz, and misc stuff
sudo apt-get update
sudo apt-get install -yq curl htop tmux pixz sshpass rsync lbzip2 pigz iptables-persistent
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-cache policy docker-ce
sudo apt-get install -yq docker-ce

# Add user to the docker group, to use docker without sudo/root
sudo usermod -aG docker $USER

# Enable ipv4 forwarding in systemd, for docker containers to map ports to the outside world
sudo sysctl -w net.ipv4.ip_forward=1
sudo systemctl restart networking.service

# Enable NAT on the master, so that workers without a public IP can access the internet through the master
sudo iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -j ACCEPT
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i eth1 -j ACCEPT
sudo sh -c "iptables-save > /etc/iptables/rules.v4"  # make the rules persistant accross reboots

# Install Miniconda

wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
chmod +x /tmp/miniconda.sh
/tmp/miniconda.sh -b -p $HOME/conda
echo "export PATH=\"\$HOME/conda/bin:\$PATH\"" >> $HOME/.bashrc
export PATH="$HOME/conda/bin:$PATH"
rm /tmp/miniconda.sh
conda install -y python=3.6

# install python dependencies

conda install -y numpy pyyaml
conda install -y -c conda-forge netifaces
# Setting specific versions of redis and rq because of https://github.com/rq/rq/issues/1014
yes | pip install --user spur softlayer redis==2.10.6 rq==0.12.0
