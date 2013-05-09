#!/usr/bin/env python
"""
- Networks:

eth0, management: inherent interface on each rVM
eth1, ops: 10.251.x.x/16
eth2, private: 10.252.x.x/16
eth3, public: 172.31.x.x/16

- Steps:

start 3 + 2 (default) or more VMs, via calling OpenStack Nova API

install chefserver, config knife, upload cookbooks, roles, and
environments

check-in all other VMs into chefserver (knife bootstrap), via eth0

deploy VXLAN network via openvswitch cookbook for all VMs, i.e., build VXLAN
tunnels with gateway as layer-2 hub and other VMs as spokes

deploy OpenStack controller(s) via misc cookbooks

deploy workers via misc cookbooks (parallelization via Python
multi-threading or multi-processing)

- Others:

rVMs eth1 IPs
[prefix]-gateway, 10.251.0.1
[prefix]-chefserver, 10.251.0.2
[prefix]-controller(s), 10.251.0.3 [ - 10.251.0.255] # maximum 253
[prefix]-worker-1, 10.251.1.1
[prefix]-worker-2(s), 10.251.1.2 [ - 10.251.255.254] # maximum ~65000

DNS: dnsmasq (disable dhcpclient from overwriting /etc/resolv.conf)

End-user input: (1) # of workers (default 2), (2) ssh_public_key. What user
data does orchestrator store?

prefix generation: gurantee uniqueness, along with a sequantially growing
number?

templatize all templatable configurations (environments, roles, etc), put the
rest (sensitive data) in a private configuration file specific to each
developer/user
"""

import os
import sys
import time
import traceback

from novaclient.v1_1 import client


def main():
    try:
        nova_client = client.Client(os.environ['OS_USERNAME'],
                                    os.environ['OS_PASSWORD'],
                                    os.environ['OS_TENANT_NAME'],
                                    os.environ['OS_AUTH_URL'])
    except Exception:
        print traceback.format_exc()
        usage()
        sys.exit(1)
    prefix = 'cliu-test'
    image = '3ab46178-eaae-46f0-8c13-6aad4d62ecde'  # u1204-130508-gv
    flavor = 3  # medium
    key_name = 'shared'
    security_groups = ("chef", "ssh", "default")
    num_instances = 3
    servers = []
    for i in xrange(num_instances):
        name = '%s-%s' % (prefix, i)
        server = nova_client.servers.create(name=name,
                                            image=image,
                                            flavor=flavor,
                                            key_name=key_name,
                                            security_groups=security_groups,
                                            )
        servers.append(server)
        print 'server %s is being created' % name
    time.sleep(20)
    for server in servers:
        # server.reboot()
        server.delete()
        print 'server %s is being deleted' % server.name
#    for flavor in nova_client.flavors.list():
#        print repr(flavor)
#    for image in nova_client.images.list():
#        print repr(image)
#    for keypair in nova_client.keypairs.list():
#        print repr(keypair)
#    for security_group in nova_client.security_groups.list():
#        print repr(security_group)
#    print nova_client.images.get('3ab46178-eaae-46f0-8c13-6aad4d62ecde')
#    print nova_client.flavors.get(3)


def usage():
    print """
    First: make sure OpenStack-related environment variables are defined

    Then: python %s
    """ % (__file__)

##############################################
if __name__ == "__main__":
    main()
