#!/usr/bin/env python

## Networks:

# Management network: 10.250.0.x/24
# Private network: 10.250.1.x/24
# Public network: 10.250.2.x/24

## VMs:

# [prefix]-gateway, 10.250.0.1
# [prefix]-chefserver, 10.250.0.2
# [prefix]-controller(s), 10.250.0.3 [ ~ 10.250.0.100]
# [prefix]-worker-1, 10.250.0.100
# [prefix]-worker-2, 10.250.0.100 [~10.250.0.254]

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
