#!/usr/bin/env python
"""
- Networks:

User /24 address for now (faster OpenStack deployment), increase to /16 later

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
                 gateway_flavor=1,
                 key_name='shared',
                 security_groups=('default', 'ssh'),
                 src_dir='../bin/',
                 dst_dir='/home/ubuntu/',
                 userdata='userdata.sh',
                 chefserver_files=('install_chefserver.sh',
                                   'configure_knife.sh',
                                   'setup_chef_repo.sh'),
                 timeout=90,
                 poll_interval=5):
        """
        @param prefix: unique name as prefix
        @param num_workers: how many worker nodes you'd like
        @param user: username (with root permission) for all servers
        @param image: default u1204-130508-gv
        @param flavor: default medium
        @param gateway_flavor: default tiny
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
        self.gateway_flavor = gateway_flavor
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
        ## non-args
        self.client = Client(os.environ['OS_USERNAME'],
                             os.environ['OS_PASSWORD'],
                             os.environ['OS_TENANT_NAME'],
                             os.environ['OS_AUTH_URL'])
        self._gateway_id = None
        self._gateway_ip = None
        self._gateway_name = None
        self._chefserver_id = None
        self._chefserver_ip = None
        self._chefserver_name = None
        self._controller_id = None
        self._controller_ip = None
        self._controller_name = None
        self._worker_ids = []
        self._worker_ips = []
        self._worker_names = []
        self._gateway_floating_ip = None

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
            self._setup_controller()
            self._setup_workers()
            print ("Your inception cloud is ready!!! gateway IP=%s" %
                   self._gateway_floating_ip.ip)
        except Exception:
            print traceback.format_exc()
            if atomic:
                self.cleanup()

    def _create_servers(self):
        """
        start all VM servers: gateway, chefserver, controller, and workers, via
        calling Nova client API
        """
        # launch gateway
        gateway = self.client.servers.create(
            name=self.prefix + '-gateway',
            image=self.image,
            flavor=self.gateway_flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            userdata=self.userdata)
        self._gateway_id = gateway.id
        print "%s is being created" % gateway.name

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

        print ('wait at most %s seconds for servers to be ready (ssh-able)' %
               self.timeout)
        servers_ready = False
        begin_time = time.time()
        while time.time() - begin_time <= self.timeout:
            try:
                # get IP addr of servers
                (self._gateway_ip, self._gateway_name) = self._get_server_info(
                    self._gateway_id)
                (self._chefserver_ip, self._chefserver_name) = (
                    self._get_server_info(self._chefserver_id))
                (self._controller_ip, self._controller_name) = (
                    self._get_server_info(self._controller_id))
                for _id in self._worker_ids:
                    (ipaddr, name) = self._get_server_info(_id)
                    self._worker_ips.append(ipaddr)
                    self._worker_names.append(name)
                # test ssh-able
                cmd.ssh(self.user + "@" + self._gateway_ip, 'true')
                cmd.ssh(self.user + "@" + self._chefserver_ip, 'true')
                cmd.ssh(self.user + "@" + self._controller_ip, 'true')
                for worker_ip in self._worker_ips:
                    cmd.ssh(self.user + "@" + worker_ip, 'true')
                # indicate that servers are ready
                servers_ready = True
                break
            except (cmd.SshConnectionError, UnboundLocalError) as error:
                print ('servers are not all ready, error=%s, sleep %s seconds'
                       % (error, self.poll_interval))
                time.sleep(self.poll_interval)
                continue
        if not servers_ready:
            raise RuntimeError("No all servers can be brought up")

        # create a public IP and associate it to gateway
        floating_ip = self.client.floating_ips.create()
        self.client.servers.add_floating_ip(self._gateway_id, floating_ip)
        self._gateway_floating_ip = floating_ip

    def _get_server_info(self, _id):
        """
        get server information (IP, hostname) from server ID

        @param _id: server ID
        """
        server = self.client.servers.get(_id)
        # get ipaddress (there is only 1 item in the dict)
        for network in server.networks:
            ipaddr = server.networks[network][0]
        return (ipaddr, server.name)

    def _setup_chefserver(self):
        """
        execute uploaded scripts to install chef, config knife, upload
        cookbooks, roles, and environments
        """
        def ssh_chefserver(command):
            return cmd.ssh(self.user + "@" + self._chefserver_ip,
                           "/bin/bash " + command, screen_output=True)
        ssh_chefserver('install_chefserver.sh')
        ssh_chefserver('configure_knife.sh')
        ssh_chefserver('setup_chef_repo.sh')

    def _checkin_chefserver(self):
        """
        check-in all VMs into chefserver (knife bootstrap), via eth0
        """
        ips = ([self._chefserver_ip, self._gateway_ip, self._controller_ip]
               + self._worker_ips)
        names = ([self._chefserver_name, self._gateway_name,
                  self._controller_name] + self._worker_names)
        for (ipaddr, name) in zip(ips, names):
            out, error = cmd.ssh(
                self.user + '@' + self._chefserver_ip,
                '/usr/bin/knife bootstrap %s -x %s -N %s --sudo' % (
                    ipaddr, self.user, name),
                screen_output=True,
                agent_forwarding=True)
            print 'out=', out, 'error=', error

    def _deploy_vxlan_network(self):
        """
        deploy VXLAN network via openvswitch cookbook for all VMs, i.e., build
        VXLAN tunnels with gateway as layer-2 hub and other VMs as spokes
        """

    def _setup_controller(self):
        """
        deploy OpenStack controller(s) via misc cookbooks
        """

    def _setup_workers(self):
        """
        deploy workers via misc cookbooks (parallelization via Python
        multi-threading or multi-processing)
        """

    def cleanup(self):
        """
        blow up the whole inception cloud
        """
        print "Let's blow up the whole inception cloud..."
        try:
            print ("floating ip %s is being released and deleted" %
                   self._gateway_floating_ip)
            self.client.servers.remove_floating_ip(self._gateway_id,
                                                   self._gateway_floating_ip)
            self.client.floating_ips.delete(self._gateway_floating_ip)
        except Exception:
            print traceback.format_exc()
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
            raise ValueError('"-" cannot exist in prefix=%r' % prefix)
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
    if shell:
        # give me a ipython shell
        IPython.embed()
        return
    orchestrator.start(atomic)


def usage():
    print """
    (make sure OpenStack-related environment variables are defined)

    python %s -p <prefix> -n <num_workers> [--shell] [--atomic]
    """ % (__file__,)

##############################################
if __name__ == "__main__":
    main()
