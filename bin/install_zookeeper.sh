#!/bin/bash

## Install ZooKeeper and OpenJDK 7

VERSION=3.4.6

sudo apt-get -y install openjdk-7-jdk

sudo mkdir -p /opt/zookeeper
sudo chmod 00777 /opt/zookeeper
sudo chown root:root /opt/zookeeper

cd /opt/zookeeper
wget http://mirrors.gigenet.com/apache/zookeeper/zookeeper-${VERSION}/zookeeper-${VERSION}.tar.gz
tar xzvf zookeeper-${VERSION}.tar.gz
mv zookeeper-${VERSION} zookeeper
cd zookeeper

sudo mkdir -p /mnt/zookeeper
sudo chmod 00777 /mnt/zookeeper
sudo chown root:root /mnt/zookeeper

echo "1" | tee /mnt/zookeeper/myid

echo "# The number of milliseconds of each tick
tickTime=2000
# The number of ticks that the initial
# synchronization phase can take
initLimit=5
# The number of ticks that can pass between
# sending a request and getting an acknowledgement
syncLimit=2
# the directory where the snapshot is stored.
# do not use /tmp for storage, /tmp here is just
# example sakes.
dataDir=/mnt/zookeeper
# the port at which the clients will connect
clientPort=2181
server.1=<zk_host_1>:2888:3888
server.2=<zk_host_2>:2888:3888
server.3=<zk_host_3>:2888:3888
# the directory where the log is stored
# dataLogDir=/mnt/zookeeper
#
# Be sure to read the maintenance section of the
# administrator guide before turning on autopurge.
#
# http://zookeeper.apache.org/doc/current/zookeeperAdmin.html#sc_maintenance
#
# The number of snapshots to retain in dataDir
#autopurge.snapRetainCount=3
# Purge task interval in hours
# Set to 0 to disable auto purge feature
#autopurge.purgeInterval=1
" | tee /opt/zookeeper/zookeeper/conf/zoo.cfg

# Start the service
# /opt/zookeeper/zookeeper/bin/zkServer.sh start
