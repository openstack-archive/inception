#!/bin/bash

# /dev/vdb is formatted and mounted on /mnt
# we need to use it as a volume for cinder instead
sudo /bin/umount /mnt/
sudo sed -i 's/\/dev\/vdb/#\/dev\/vdb/g' /etc/fstab
sudo parted /dev/vdb --script -- mklabel gpt
sudo parted /dev/vdb --script -- mkpart primary ext4 1 -1
sudo parted /dev/vdb --script -- set 1 lvm on

# use dnsmasq (fixed resolv.conf) instead
sudo apt-get -y remove resolvconf || true

# shorten sleep time of failsafe and cloud-init-nonet
sudo sed -i -e 's/sleep\ 20/sleep\ 1/g' -e 's/sleep\ 40/sleep\ 1/g' \
	-e 's/sleep\ 59/sleep\ 1/g' /etc/init/failsafe.conf
sudo sed -i 's/long=120/long=20/g' /etc/init/cloud-init-nonet.conf
