#!/usr/bin/env python

## Networks:

# eth0, management: inherent interface on each rVM
# eth1, ops: 10.251.x.x/16
# eth2, private: 10.252.x.x/16
# eth3, public: 172.31.x.x/16

## rVMs (eth1, ops interface)

# [prefix]-gateway, 10.251.0.1
# [prefix]-chefserver, 10.251.0.2
# [prefix]-controller(s), 10.251.0.3 [ - 10.251.0.255] # maximum 253
# [prefix]-worker-1, 10.251.1.1
# [prefix]-worker-2(s), 10.251.1.2 [ - 10.251.255.254] # maximum ~65000

## Steps:

# start 3 + 2 (or more) VMs, via calling OpenStack Nova API

# install chefserver, config knife, upload cookbooks, roles, and
# environments

# check-in (bootstrap) 4 (or more) VMs into chefserver

# deploy VXLAN network via cookbook for all VMs, with gateway as
# layer-2 hub and other VMs as spokes

# deploy OpenStack controller(s) via misc cookbooks

# deploy workers via misc cookbooks (parallelization via Python
# multi-threading or multi-processing)
