#!/bin/bash

## Install Open vSwitch (2.0.0). This file is translated from
## cookbook/openvswitch/recipes/default

# dependencies
sudo apt-get -y install build-essential \
    git \
    autoconf \
    python-dev \
    python-simplejson \
    python-qt4 \
    python-twisted-conch \
    uml-utilities \
    libtool \
    libssl-dev \
    pkg-config

sudo mkdir -p /opt/openvswitch
sudo chmod 00755 /opt/openvswitch
sudo chown root:root /opt/openvswitch

sudo mkdir -p /etc/openvswitch
sudo chmod 00755 /etc/openvswitch
sudo chown root:root /etc/openvswitch

sudo chmod a+w /opt/openvswitch
cd /opt/openvswitch
wget http://openvswitch.org/releases/openvswitch-2.0.0.tar.gz
tar xzvf openvswitch-2.0.0.tar.gz
mv openvswitch-2.0.0 openvswitch
cd openvswitch
./configure --with-linux=/lib/modules/`uname -r`/build \
    --prefix=/usr --localstatedir=/var # default to these libraries
make -j
sudo make install
sudo make modules_install
sudo ovsdb-tool create /etc/openvswitch/conf.db \
    vswitchd/vswitch.ovsschema
sudo /usr/bin/ovs-vsctl --no-wait init

echo "start on (filesystem and net-device-up)
stop on runlevel [016]

# Automatically restart process if crashed
respawn

# Essentially lets upstart know the process will detach itself to the background
expect fork

pre-start script
  /sbin/modprobe openvswitch
  /sbin/modprobe gre
  mkdir -p /var/run/openvswitch/
end script

script
  exec /usr/sbin/ovsdb-server /etc/openvswitch/conf.db \\
        --remote=punix:/var/run/openvswitch/db.sock \\
        --remote=db:Open_vSwitch,Open_vSwitch,manager_options \\
        --private-key=db:Open_vSwitch,SSL,private_key \\
        --certificate=db:Open_vSwitch,SSL,certificate \\
        --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \\
        --pidfile --detach
end script

# seems main script only allows one daemon, so we move another
# daemon(s) to post-start and pre-stop
post-start script
  exec /usr/sbin/ovs-vswitchd --pidfile --detach
end script

pre-stop script
  exec killall -9 ovs-vswitchd
end script

post-stop script
  /sbin/rmmod openvswitch
end script
" | sudo tee /etc/init/openvswitch.conf
sudo chmod 00755 /etc/init/openvswitch.conf
sudo chown root:root /etc/init/openvswitch.conf

sudo service openvswitch start
