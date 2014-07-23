#!/bin/bash

## Install libvirt (1.2.0), and enable VM (KVM/Qemu) live
## migration. Default libvirt on Ubuntu 12.04 is 0.9.8, which does not
## work well with Open vSwitch ("<virtualport type='openvswitch'/>"
## cannot be added into VM xml configuration).

# Install KVM, QEMU and libvirt (0.9.8, so that we have /etc/init/libvirt-bin.conf)
sudo apt-get -y install \
    kvm \
    qemu \
    libvirt-bin

# Install dependencies. You can omit the libcurl4-gnutls-dev package
# if you don’t want ESX support.
sudo apt-get update
sudo apt-get -y install \
    gcc \
    make \
    pkg-config \
    libxml2-dev \
    libgnutls-dev \
    libdevmapper-dev \
    libcurl4-gnutls-dev \
    python-dev \
    libpciaccess-dev \
    libxen-dev \
    libyajl-dev \
    libnl-dev

sudo mkdir -p /opt/libvirt
sudo chmod 00755 /opt/libvirt
sudo chown root:root /opt/libvirt

sudo chmod a+w /opt/libvirt
cd /opt/libvirt
wget http://libvirt.org/sources/libvirt-1.2.0.tar.gz
tar xzvf libvirt-1.2.0.tar.gz
mv libvirt-1.2.0 libvirt
cd libvirt
./configure \
    --prefix=/usr \
    --localstatedir=/var \
    --sysconfdir=/etc \
    --with-esx=yes \
    --with-xen=yes # if you need Xen support, you’ll need to add
		   # --with-xen=yes to the command
make -j
sudo make install
