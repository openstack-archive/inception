#!/bin/bash

CONTROLLERS=$@

docker.io rm -f `docker.io ps -a | grep changbl | awk '{print $1}'`

for i in `ovs-vsctl show | grep Port | grep pl | awk '{print $2}' | cut -d '"' -f 2`
do
    ovs-vsctl del-port obr2 $i
done
