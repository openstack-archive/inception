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

# enable libvirt for VM live migration
sudo sed -i /etc/libvirt/libvirtd.conf \
    -e 's/#listen_tls = 0/listen_tls = 0/g' \
    -e 's/#listen_tcp = 1/listen_tcp = 1/g' \
    -e 's/#auth_tcp = "sasl"/auth_tcp = "none"/g'
sudo sed -i /etc/init/libvirt-bin.conf \
    -e 's/env libvirtd_opts="-d"/env libvirtd_opts="-d -l"/g'
sudo sed -i /etc/default/libvirt-bin \
    -e 's/libvirtd_opts="-d"/libvirtd_opts="-d -l"/g'

# restart libvirt
sudo service libvirt-bin restart

# Remove the default network created by libvirt
sudo virsh net-destroy default
sudo virsh net-undefine default
