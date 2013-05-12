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
                 userdata='userdata.sh',
                 chefserver_files=('install_chefserver.sh',
                                   'configure_knife.sh',
                                   'setup_chef_repo.sh'),
                 timeout=45,
                 poll_interval=5):
        """
        @param prefix: unique name as prefix
        @param num_workers: how many worker nodes you'd like
        @param image: default u1204-130508-gv
        @param flavor: default medium
        @param key_name: ssh public key to be injected
        @param security_groups:
        @param src_dir: location from where scripts are uploaded to servers.
            Relative path to __file__
        @param dst_dir: target location of scripts on servers. Must be absolte
            path
        @param userdata: a bash script to be executed by cloud-init (in late
            booting stage, rc.local-like)
        @param chefserver_files: scripts to run on chefserver. Scripts will
            be executed one by one, so sequence matters
        @param timeout: sleep time (s) for servers to be launched
        @param poll_interval: every this time poll to check whether a server
            has finished launching, i.e., ssh-able
        """
        ## args
        self.prefix = prefix
        self.num_workers = num_workers
        self.user = user
        self.image = image
        self.flavor = flavor
        self.key_name = key_name
        self.security_groups = security_groups
        self.src_dir = os.path.join(os.path.abspath(
            os.path.dirname(__file__)), src_dir)
        self.dst_dir = os.path.abspath(dst_dir)
        with open(os.path.join(self.src_dir, userdata), 'r') as fin:
            self.userdata = fin.read()
        self.chefserver_files = OrderedDict()
        for filename in chefserver_files:
            with open(os.path.join(self.src_dir, filename), 'r') as fin:
                value = fin.read()
                key = os.path.join(self.dst_dir, filename)
                self.chefserver_files[key] = value
        self.timeout = timeout
        self.poll_interval = poll_interval
        ## entities
        self.client = Client(os.environ['OS_USERNAME'],
                             os.environ['OS_PASSWORD'],
                             os.environ['OS_TENANT_NAME'],
                             os.environ['OS_AUTH_URL'])
        self._chefserver_id = None
        self._chefserver_ip = None
        self._gateway_id = None
        self._gateway_ip = None
        self._controller_id = None
        self._controller_ip = None
        self._worker_ids = []
        self._worker_ips = []

    def start(self, atomic):
        """
        run the whole process

        @param atomic: upon exception, whether rollback, i.e., auto delete all
            created servers
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
            if atomic:
                self.cleanup()

    def _create_servers(self):
        """
        start all VM servers: chefserver, gateway, controller, and workers, via
        calling Nova client API
        """
        # launch chefserver
        chefserver = self.client.servers.create(
            name=self.prefix + '-chefserver',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            userdata=self.userdata,
            files=self.chefserver_files)
        self._chefserver_id = chefserver.id
        print "%s is being created" % chefserver.name

        # launch gateway
        gateway = self.client.servers.create(
            name=self.prefix + '-gateway',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            userdata=self.userdata)
        self._gateway_id = gateway.id
        print "%s is being created" % gateway.name

        # launch controller
        controller = self.client.servers.create(
            name=self.prefix + '-controller',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            userdata=self.userdata)
        self._controller_id = controller.id
        print "%s is being created" % controller.name

        # launch workers
        for i in xrange(self.num_workers):
            worker = self.client.servers.create(
                name=self.prefix + '-worker%s' % (i + 1),
                image=self.image,
                flavor=self.flavor,
                key_name=self.key_name,
                security_groups=self.security_groups,
                userdata=self.userdata)
            self._worker_ids.append(worker.id)
            print 'name %s is being created' % worker.name

        # TODO: poll to test whether ssh-able
        #if chefserver.status != 'ACTIVE':
        #    raise RuntimeError('%s can not be launched' % chefserver.name)
        print 'sleep %s seconds to wait for servers to be ready' % self.timeout
        time.sleep(self.timeout)

        # get IP addr of servers
        self._chefserver_ip = self._get_server_ip(self._chefserver_id)
        self._gateway_ip = self._get_server_ip(self._gateway_id)
        self._controller_ip = self._get_server_ip(self._controller_id)
        self._worker_ips = [self._get_server_ip(_id)
                            for _id in self._worker_ids]

    def _get_server_ip(self, _id):
        """
        get server IP from server ID
        """
        server = self.client.servers.get(_id)
        # get ipaddress (there is only 1 item in the dict)
        for network in server.networks:
            ipaddress = server.networks[network][0]
        return ipaddress

    def _setup_chefserver(self):
        """
        execute uploaded scripts to install chef, config knife, upload
        cookbooks, roles, and environments
        """
        for key in self.chefserver_files:
            out, error = cmd.ssh(self.user + '@' + self._chefserver_ip,
                                 '/bin/bash ' + key,
                                 screen_output=True)
            print 'out=', out, 'error=', error

    def _checkin_chefserver(self):
        """
        check-in all VMs into chefserver (knife bootstrap), via eth0
        """
        #FIXME: can not check in myself (chefserver), causing problem
        ips = ([self._gateway_ip, self._controller_ip] + self._worker_ips)
        for ip in ips:
            out, error = cmd.ssh(
                self.user + '@' + self._chefserver_ip,
                '/usr/bin/knife bootstrap %s -x %s --sudo' % (ip, self.user),
                screen_output=True,
                agent_forwarding=True)
            print 'out=', out, 'error=', error

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

    def cleanup(self):
        """
        blow up the whole inception cloud
        """
        print "blow up the whole inception cloud..."
        ids = ([self._chefserver_id, self._gateway_id, self._controller_id] +
               self._worker_ids)
        for _id in ids:
            try:
                server = self.client.servers.get(_id)
                server.delete()
                print '%s is being deleted' % server.name
            except Exception:
                print traceback.format_exc()
                continue


def main():
    """
    program starting point
    """
    shell = False
    atomic = False
    try:
        optlist, _ = getopt.getopt(sys.argv[1:], 'p:n:', ["shell", "atomic"])
        optdict = dict(optlist)
        prefix = optdict['-p']
        if '-' in prefix:
            raise RuntimeError('"-" can not exist in prefix')
        num_workers = int(optdict['-n'])
        if "--shell" in optdict:
            shell = True
        if "--atomic" in optdict:
            atomic = True
    except Exception:
        print traceback.format_exc()
        usage()
        sys.exit(1)
    orchestrator = Orchestrator(prefix, num_workers)
    orchestrator.start(atomic)
    # give me a ipython shell after inception cloud is launched
    if shell:
        IPython.embed()


def usage():
    print """
    (make sure OpenStack-related environment variables are defined)

    python %s -p <prefix> -n <num_workers> [--shell] [--atomic]
    """ % (__file__,)

##############################################
if __name__ == "__main__":
    main()
