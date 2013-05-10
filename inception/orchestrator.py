#!/usr/bin/env python
"""
TODOs

- Networks:

eth0, management: inherent interface on each rVM
eth1, ops: 10.251.x.x/16
eth2, private: 10.252.x.x/16
eth3, public: 172.31.x.x/16

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

import getopt
import os
import sys
import time
import traceback
from collections import OrderedDict

import IPython
from novaclient.v1_1.client import Client

from inception.utils import cmd


class Orchestrator(object):
    """
    orchestrate all inception cloud stuff
    """

    def __init__(self,
                 prefix,
                 num_workers,
                 user='ubuntu',
                 image='3ab46178-eaae-46f0-8c13-6aad4d62ecde',
                 flavor=3,
                 key_name='shared',
                 security_groups=('default', 'ssh'),
                 src_dir='../bin/',
                 dst_dir='/home/ubuntu/',
                 chefserver_filenames=('install_chefserver.sh',
                                       'configure_knife.sh',
                                       'setup_chef_repo.sh'),
                 timeout=60):
        """
        @param prefix: unique name as prefix
        @param num_workers: how many worker nodes you'd like
        @param image: default u1204-130508-gv
        @param flavor: default medium
        @param key_name: ssh public key to be injected
        @param security_groups:
        @param src_dir: location from where scripts are uploaded to servers
        @param dst_dir: target location of scripts on servers
        @param chefserver_filenames: scripts to run on chefserver
        @param timeout: sleep time (s) for servers to be launched
        """
        ## args
        self.prefix = prefix
        self.num_workers = num_workers
        self.user = user
        self.image = image
        self.flavor = flavor
        self.key_name = key_name
        self.security_groups = security_groups
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.chefserver_files = OrderedDict()
        for filename in chefserver_filenames:
            fin = open(os.path.join(self.src_dir, filename), 'r')
            value = fin.read()
            key = os.path.join(self.dst_dir, filename)
            self.chefserver_files[key] = value
            fin.close()
        self.timeout = timeout
        ## entities
        self.client = Client(os.environ['OS_USERNAME'],
                             os.environ['OS_PASSWORD'],
                             os.environ['OS_TENANT_NAME'],
                             os.environ['OS_AUTH_URL'])
        self.chefserver = None
        self.gateway = None
        self.controller = None
        self.workers = []

    def start(self):
        """
        run the whole process
        """
        try:
            self._create_servers()
            self._setup_chefserver()
            self._checkin_chefserver()
            self._deploy_vxlan_network()
            self._deploy_controller()
            self._deploy_workers()
            print "Your inception cloud is ready!!!"
        except Exception:
            print traceback.format_exc()
            self._cleanup()

    def _create_servers(self):
        """
        start all VM servers: chefserver, gateway, controller, and workers, via
        calling Nova client API
        """
        # launch chefserver
        self.chefserver = self.client.servers.create(
            name=self.prefix + '-chefserver',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            files=self.chefserver_files)
        print "%s is being created" % self.chefserver.name

        # launch gateway
        self.gateway = self.client.servers.create(
            name=self.prefix + '-gateway',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups)
        print "%s is being created" % self.gateway.name

        # launch controller
        self.controller = self.client.servers.create(
            name=self.prefix + '-controller',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups)
        print "%s is being created" % self.controller.name

        # launch workers
        self.workers = []
        for i in xrange(self.num_workers):
            worker = self.client.servers.create(
                name=self.prefix + '-worker%s' % (i + 1),
                image=self.image,
                flavor=self.flavor,
                key_name=self.key_name,
                security_groups=self.security_groups)
            self.workers.append(worker)
            print 'name %s is being created' % worker.name

        print 'sleep %s seconds to wait for servers to be ready' % self.timeout
        time.sleep(self.timeout)

    def _setup_chefserver(self):
        """
        execute uploaded scripts to install chef, config knife, upload
        cookbooks, roles, and environments
        """
        self.chefserver = self.client.servers.get(self.chefserver.id)
        if self.chefserver.status != 'ACTIVE':
            raise RuntimeError('%s can not be launched' % self.chefserver.name)
        # get ipaddress (there is only 1 item in the dict)
        for network in self.chefserver.networks:
            ipaddress = self.chefserver.networks[network][0]
        # execute scripts via ssh command
        out, error = cmd.ssh(self.user + '@' + ipaddress,
                             'sudo /bin/umount /mnt')
        print 'out=', out, 'error=', error
        for key in self.chefserver_files:
            out, error = cmd.ssh(self.user + '@' + ipaddress,
                                 '/bin/bash ' + key,
                                 output_to_screen=True)
            print 'out=', out, 'error=', error

    def _checkin_chefserver(self):
        """
        check-in all other VMs into chefserver (knife bootstrap), via eth0
        """

    def _deploy_vxlan_network(self):
        """
        deploy VXLAN network via openvswitch cookbook for all VMs, i.e., build
        VXLAN tunnels with gateway as layer-2 hub and other VMs as spokes
        """

    def _deploy_controller(self):
        """
        deploy OpenStack controller(s) via misc cookbooks
        """

    def _deploy_workers(self):
        """
        deploy workers via misc cookbooks (parallelization via Python
        multi-threading or multi-processing)
        """

    def _cleanup(self):
        """
        blow up the whole inception cloud
        """
        for server in self.client.servers:
            server.delete()
            print '%s is being deleted' % server.name


def main():
    """
    program starting point
    """
    try:
        optlist, _ = getopt.getopt(sys.argv[1:], 'p:n:', [])
        optdict = dict(optlist)
        prefix = optdict['-p']
        if '-' in prefix:
            raise RuntimeError('"-" can not exist in prefix')
        num_workers = int(optdict['-n'])
    except Exception:
        print traceback.format_exc()
        usage()
        sys.exit(1)
    orchestrator = Orchestrator(prefix, num_workers)
    orchestrator.start()
    # give me a ipython shell when everything is done
    IPython.embed()


def usage():
    print """
    (make sure OpenStack-related environment variables are defined)

    python %s -p <prefix> -n <num_workers>
    """ % (__file__,)

##############################################
if __name__ == "__main__":
    main()
