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
