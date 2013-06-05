#!/bin/bash

## Switch kernel from virtual to generic, for vanilla Ubuntu 12.04
## image launched instance.

# routine
sudo apt-get -y update
sudo apt-get -y upgrade

# install generic and reomve virtual kernel
sudo apt-get -y install linux-generic
sudo apt-get -y purge linux-virtual

# cleanup
sudo apt-get -y autoremove
sudo apt-get -y autoclean

# reboot
sudo reboot
