#!/usr/bin/env python

import sys
import os

BRIDGE="obr2"
#BRIDGE="br2"
GATEWAY="10.2.2.10"
NET_PREFIX="10.2"
MAC_ADDR_PREFIX="52:54:00:2d:"
IMAGE="changbl/u1404-3"

def int_to_hex(n):
    if not 1 <= n <= 254:
        raise KeyError('Wrong value: number not within [1, 254]')
    s = hex(n)[2:]
    if len(s) == 2:
        return s
    else:
        return '0' + s

def launch(subnet, begin, end):
    for i in range(begin, end):
        name = "%s.%s" % (subnet, i)
        mac_addr = (MAC_ADDR_PREFIX + "%s:%s" % (
            int_to_hex(subnet), int_to_hex(i)))

#         cmd = """/root/pipework %s -i eth0 $(\
# docker.io run --privileged=true -n=false --name=%s -d %s /usr/sbin/sshd -D\
# ) %s.%s.%s/16@%s %s""" % (
#     BRIDGE, name, IMAGE, NET_PREFIX, subnet, i, GATEWAY, mac_addr)

        cmd = """/root/pipework %s -i eth0 $(\
docker.io run -n=false --privileged=true --name=%s -d %s /usr/sbin/sshd -D\
) dhcp %s""" % (
    BRIDGE, name, IMAGE, mac_addr)

        print cmd
        os.system(cmd)

"""
docker.io run --privileged=true -d -n=false \
    -lxc-conf="lxc.network.type = veth" \
    -lxc-conf="lxc.network.link = br2" \
    -lxc-conf="lxc.network.flags = up" \
    -lxc-conf="lxc.network.name = eth0" \
    -lxc-conf="lxc.network.ipv4 = 10.2.101.3/16" \
    -lxc-conf="lxc.network.hwaddr=52:54:00:2d:65:03" \
    -lxc-conf="lxc.network.ipv4.gateway = 10.2.1.10" \
    --name=101.3 changbl/u1401-1 /usr/sbin/sshd -D

ID=$(docker.io run -n=false --name=test4 -d changbl/u1404-2 /usr/sbin/sshd -D)

./pipework obr2 -i eth0 $ID dhcp 52:54:00:2d:c9:04

./pipework obr2 -i eth0 $ID 10.2.201.8/16@10.2.2.10 52:54:00:2d:c9:08

docker.io inspect da1fbd5421f7 | grep ID 

lxc-attach -n da1fbd5421f75ef1a640019d4659489ee53faf4135f4e6feeb8872580f74549a -- /bin/bash
"""
#         cmd = """docker.io run --privileged=true -d -n=false \
# -lxc-conf="lxc.network.type = veth" \
# -lxc-conf="lxc.network.link = %s" \
# -lxc-conf="lxc.network.flags = up" \
# -lxc-conf="lxc.network.name = eth0" \
# -lxc-conf="lxc.network.ipv4 = %s.%s.%s/16" \
# -lxc-conf="lxc.network.hwaddr=%s" \
# -lxc-conf="lxc.network.ipv4.gateway = %s" \
# --name=%s \
# %s /usr/sbin/sshd -D""" % (
#     BRIDGE, NET_PREFIX, subnet, i, mac_addr, GATEWAY, name, IMAGE)
#

if __name__ == "__main__":
    subnet = int(sys.argv[1])
    begin = int(sys.argv[2])
    end = int(sys.argv[3])
    launch(subnet, begin, end)
