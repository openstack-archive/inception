#!/usr/bin/env python
"""
- Networks:

(use /24 address for now (faster OpenStack deployment), increase to /16 later)

eth0, management: inherent interface on each rVM
eth1, ops: 10.251.x.x/16
eth2, private: 10.252.x.x/16
eth3, public: 172.31.x.x/16

rVMs eth1 IPs
[prefix]-gateway, 10.251.0.1
[prefix]-chefserver, 10.251.0.2
[prefix]-controller(s), 10.251.0.3 [ - 10.251.0.255] # maximum 253
[prefix]-worker-1, 10.251.1.1
[prefix]-worker-2(s), 10.251.1.2 [ - 10.251.255.254] # maximum ~65000

webui: end-user input: (1) # of workers (default 2), (2) ssh_public_key

templatize all templatable configurations (environments, roles, etc), put the
rest (sensitive data) in a private configuration file specific to each
developer/user
"""

import getopt
import os
import sys
import threading
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
                 chef_repo,
                 chef_repo_branch,
                 sequential,
                 user='ubuntu',
                 image='38b0b5a5-7dda-4fd1-b53a-00ba47eacc16',
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
                 timeout=999999,
                 poll_interval=5):
        """
        @param prefix: unique name as prefix
        @param num_workers: how many worker nodes you'd like
        @param chef_repo: chef repository location
        @param chef_repo_branch: which branch to use in repo
        @param sequential: whether run threads in sequential or parallel
            (for accelerating)
        @param user: username (with root permission) for all servers
        @param image: default u1204-130529-gvc
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
        @param timeout: sleep time (s) for servers to be launched
        @param poll_interval: every this time poll to check whether a server
            has finished launching, i.e., ssh-able
        """
        ## check args
        if num_workers > 5:
            raise ValueError("currently only supports num_workers <= 5")
        if '-' in prefix:
            raise ValueError('"-" cannot exist in prefix=%r' % prefix)
        ## args
        self.prefix = prefix
        self.num_workers = num_workers
        self.chef_repo = chef_repo
        self.chef_repo_branch = chef_repo_branch
        self.sequential = sequential
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
        self.timeout = timeout
        self.poll_interval = poll_interval
        # scripts to run on chefserver, execute one by one (sequence matters)
        self.chefserver_commands = []
        self.chefserver_files = OrderedDict()
        for filename in ('install_chefserver.sh', 'configure_knife.sh',
                         'setup_chef_repo.sh'):
            src_file = os.path.join(self.src_dir, filename)
            dst_file = os.path.join(self.dst_dir, filename)
            if filename == 'setup_chef_repo.sh':
                # add two args to this command
                command = ("/bin/bash" + " " + dst_file + " " +
                           self.chef_repo + " " + self.chef_repo_branch)
            else:
                command = "/bin/bash" + " " + dst_file
            self.chefserver_commands.append(command)
            with open(src_file, 'r') as fin:
                value = fin.read()
                key = dst_file
                self.chefserver_files[key] = value
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
            self._check_existence()
            self._create_servers()
            self._setup_chefserver()
            self._checkin_chefserver()
            self._deploy_network_vxlan()
            self._deploy_dnsmasq()
            self._setup_controller()
            self._setup_workers()
            print "Your inception cloud '%s' is ready!!!" % self.prefix
            print "Gateway IP is %s" % self._gateway_floating_ip.ip
            print "Chef server WebUI is http://%s:4040" % self._chefserver_ip
            print "OpenStack dashboard is https://%s" % self._controller_ip
        except Exception:
            print traceback.format_exc()
            if atomic:
                self.cleanup()

    def _check_existence(self):
        """
        Check whether inception cloud existence based on given self.prefix
        """
        for server in self.client.servers.list():
            if '-' in server.name and server.name.split('-')[0] == self.prefix:
                raise ValueError('prefix=%s is already used' % self.prefix)

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
        print "Creating %s" % gateway

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
        print "Creating %s" % chefserver

        # launch controller
        controller = self.client.servers.create(
            name=self.prefix + '-controller',
            image=self.image,
            flavor=self.flavor,
            key_name=self.key_name,
            security_groups=self.security_groups,
            userdata=self.userdata)
        self._controller_id = controller.id
        print "Creating %s" % controller

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
            print "Creating %s" % worker

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
        print "Creating and associating %s" % floating_ip

    def _get_server_info(self, _id):
        """
        get server information (IP, hostname) from server ID

        @param _id: server ID
        """
        server = self.client.servers.get(_id)
        # get ipaddress (there is only 1 item in the dict)
        for key in server.networks:
            ipaddr = server.networks[key][0]
        return (ipaddr, server.name)

    def _setup_chefserver(self):
        """
        execute uploaded scripts to install chef, config knife, upload
        cookbooks, roles, and environments
        """
        for command in self.chefserver_commands:
            cmd.ssh(self.user + "@" + self._chefserver_ip,
                    command, screen_output=True)

    def _checkin_chefserver(self):
        """
        check-in all VMs into chefserver (knife bootstrap), and set their
        environment to be self.prefix
        """
        threads = []
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        for (ipaddr, hostname) in zip(ipaddrs, hostnames):
            uri = self.user + '@' + self._chefserver_ip
            command = ('/usr/bin/knife bootstrap %s -x %s -N %s -E %s --sudo'
                       % (ipaddr, self.user, hostname, self.prefix))
            thread = threading.Thread(target=cmd.ssh,
                                      args=(uri, command),
                                      kwargs={"screen_output": True,
                                              "agent_forwarding": True})
            threads.append(thread)
        self._run_threads(threads)
        # run an empty list to make sure attributes are properly propagated
        self._run_chef_client(ipaddrs)

    def _deploy_network_vxlan(self):
        """
        deploy network-vxlan (recipe) via cookbook openvswitch for all VMs,
        i.e., build VXLAN tunnels with gateway as layer-2 hub and other VMs
        as spokes, and assign ip address and netmask
        """
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        self._add_run_list(hostnames, 'recipe[openvswitch::network-vxlan]')
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        self._run_chef_client(ipaddrs)

    def _deploy_dnsmasq(self):
        """
        deploy dnsmasq (recipe) via cookbook openvswitch for all VMs,
        i.e., install and config on dnsmasq on gateway node, and point all
        VMs to gateway as nameserver
        """
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        self._add_run_list(hostnames, 'recipe[openvswitch::dnsmasq]')
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        self._run_chef_client(ipaddrs)

    def _add_run_list(self, hostnames, item):
        """
        for each server, add an item to its run_list

        @param hostnames: hostnames of specified servers
        @param item: name of the item (e.g., recipe, role, etc)
        """
        threads = []
        for hostname in hostnames:
            uri = self.user + '@' + self._chefserver_ip
            command = "/usr/bin/knife node run_list add %s %s" % (
                hostname, item)
            thread = threading.Thread(target=cmd.ssh,
                                      args=(uri, command),
                                      kwargs={"screen_output": True,
                                              "agent_forwarding": True})
            threads.append(thread)
        self._run_threads(threads)

    def _run_chef_client(self, ipaddrs):
        """
        for each server in the address list, run chef-client for all
        specified cookbooks in its run_list

        @param param: ip addresses of the servers
        """
        threads = []
        for ipaddr in ipaddrs:
            uri = self.user + '@' + ipaddr
            command = "sudo chef-client"
            thread = threading.Thread(target=cmd.ssh,
                                      args=(uri, command),
                                      kwargs={"screen_output": True,
                                              "agent_forwarding": True})
            threads.append(thread)
        self._run_threads(threads)

    def _run_threads(self, threads):
        """
        run threads, whether in a sequential or parallel way

        @param threads: the threads to be run
        """
        if self.sequential:
            for thread in threads:
                thread.start()
                thread.join()
        else:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

    def _setup_controller(self):
        """
        deploy OpenStack controller(s) via misc cookbooks
        """
        self._add_run_list([self._controller_name], "role[os-dev-mode]")
        self._add_run_list([self._controller_name],
                           "role[os-controller-combined]")
        self._run_chef_client([self._controller_ip])

    def _setup_workers(self):
        """
        deploy workers via misc cookbooks
        """
        self._add_run_list(self._worker_names, "role[os-dev-mode]")
        self._add_run_list(self._worker_names, "role[os-worker-combined]")
        self._run_chef_client(self._worker_ips)

    def cleanup(self):
        """
        Clean up the whole inception cloud, based on self.prefix
        """
        print "Let's clean up inception cloud '%s'..." % self.prefix
        ## find out servers info
        servers = []
        gateway = None
        gateway_ip = None
        for server in self.client.servers.list():
            if '-' in server.name and server.name.split('-')[0] == self.prefix:
                servers.append(server)
            if server.name == self.prefix + '-gateway':
                gateway = server
                # get ipaddress (there is only 1 item in the dict)
                for key in gateway.networks:
                    if len(gateway.networks[key]) >= 2:
                        gateway_ip = gateway.networks[key][1]
        ## try deleting the floating IP of gateway
        try:
            for floating_ip in self.client.floating_ips.list():
                if floating_ip.ip == gateway_ip:
                    print ("Disassociating and releasing %s" % floating_ip)
                    self.client.servers.remove_floating_ip(gateway,
                                                           floating_ip)
                    self.client.floating_ips.delete(floating_ip)
        except Exception:
            print traceback.format_exc()
        ## try deleting each server
        for server in servers:
            try:
                print 'Deleting %s' % server
                server.delete()
            except Exception:
                print traceback.format_exc()
                continue
        print "Inception cloud '%s' has been cleaned up." % self.prefix


def main():
    """
    program starting point
    """
    shell = False
    atomic = False
    cleanup = False
    chef_repo = "git://github.com/maoy/inception-chef-repo.git"
    chef_repo_branch = "master"
    sequential = False
    try:
        optlist, _ = getopt.getopt(sys.argv[1:], 'p:n:',
                                   ["shell", "atomic", "cleanup", "sequential",
                                    "chef-repo=", "chef-repo-branch="])
        optdict = dict(optlist)
        prefix = optdict['-p']
        num_workers = int(optdict['-n'])
        if "--shell" in optdict:
            shell = True
        if "--atomic" in optdict:
            atomic = True
        if "--cleanup" in optdict:
            cleanup = True
        if "--chef-repo" in optdict:
            chef_repo = optdict["--chef-repo"]
        if "--chef-repo-branch" in optdict:
            chef_repo_branch = optdict["--chef-repo-branch"]
        if "--sequential" in optdict:
            sequential = True
    except Exception:
        print traceback.format_exc()
        usage()
        sys.exit(1)
    orchestrator = Orchestrator(prefix, num_workers, chef_repo,
                                chef_repo_branch, sequential)
    if shell:
        # give me a ipython shell
        IPython.embed()
        return
    if cleanup:
        orchestrator.cleanup()
    else:
        orchestrator.start(atomic)


def usage():
    print """
python %s -p <prefix> -n <num_workers> [--shell] [--atomic] [--cleanup]
  [--sequential] [--chef-repo=git://github.com/maoy/inception-chef-repo.git]
  [--chef-repo-branch=master]

Note: make sure OpenStack-related environment variables are defined.
""" % (__file__,)

##############################################
if __name__ == "__main__":
    main()
