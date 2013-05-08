#!/usr/bin/env python

## Networks:

# eth0, management: inherent interface on each rVM
# eth1, ops: 10.251.x.x/16
# eth2, private: 10.252.x.x/16
# eth3, public: 172.31.x.x/16

## Steps:

# start 3 + 2 (default) or more VMs, via calling OpenStack Nova API

# install chefserver, config knife, upload cookbooks, roles, and
# environments

# check-in all other VMs into chefserver (knife bootstrap), via eth0

# deploy VXLAN network via openvswitch cookbook for all VMs, i.e., build VXLAN
# tunnels with gateway as layer-2 hub and other VMs as spokes

# deploy OpenStack controller(s) via misc cookbooks

# deploy workers via misc cookbooks (parallelization via Python
# multi-threading or multi-processing)

## Others:

# rVMs eth1 IPs
# [prefix]-gateway, 10.251.0.1
# [prefix]-chefserver, 10.251.0.2
# [prefix]-controller(s), 10.251.0.3 [ - 10.251.0.255] # maximum 253
# [prefix]-worker-1, 10.251.1.1
# [prefix]-worker-2(s), 10.251.1.2 [ - 10.251.255.254] # maximum ~65000

# DNS: poor man's solution, i.e., modify /etc/hosts

# End-user input: (1) # of workers (default 2), (2) ssh_public_key. What user
# data does orchestrator store?

# prefix generation: gurantee uniqueness, along with a sequantially growing
# number?

# templatize all templatable configurations (environments, roles, etc), put the
# rest (sensitive data) in a private configuration file specific to each
# developer/user
