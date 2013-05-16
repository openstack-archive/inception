#!/bin/bash

# umount extra volume not needed by OpenStack
sudo /bin/umount /mnt/

# use dnsmasq (fixed resolv.conf) instead
sudo apt-get -y remove resolvconf
