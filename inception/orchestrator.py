#!/usr/bin/env python
"""
#TODO(changbl)
Networks:
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

#TODO(to-be-assigned)
WebUI: Horizon-based

#TODO(to-be-assigned)
templatize all templatable configurations (environments, roles, etc), put the
rest (sensitive data) in a private configuration file specific to each
developer/user
"""

from collections import OrderedDict
import functools
import os
import Queue
import subprocess
import sys
import time
import traceback

import IPython
from novaclient.v1_1.client import Client
from oslo.config import cfg

from inception import __version__
from inception.utils import cmd
from inception.utils import wrapper

orchestrator_opts = [
    cfg.StrOpt('prefix',
               default=None,
               required=True,
               short='p',
               help='unique prefix for node names (no hyphens allowed)'),
    cfg.IntOpt('num_workers',
               default=2,
               short='n',
               help='number of worker nodes to create'),
    cfg.BoolOpt('atomic',
                default=False,
                help='on error, whether rollback, i.e., auto delete all'
                     ' created virtual resources'),
    cfg.BoolOpt('parallel',
                default=False,
                help='execute Chef-related setup tasks in parallel'),
    cfg.StrOpt('chef_repo',
               default='git://github.com/maoy/inception-chef-repo.git',
               help='URL of Chef repository'),
    cfg.StrOpt('chef_repo_branch',
               default='master',
               help='name of branch of Chef repo to use'),
    cfg.StrOpt('ssh_keyfile',
               default=None,
               help='path of extra public key(s) for node access via ssh'),
    cfg.StrOpt('pool',
               default='research',
               help='name of pool for floating IP addresses'),
    cfg.StrOpt('user',
               default='ubuntu',
               help='login id with sudo for all nodes'),
    cfg.StrOpt('image',
               default='f3d62d5b-a76b-4997-a579-ff946a606132',
               help='id of image used to construct nodes (=u1204-130531-gv)'),
    cfg.IntOpt('flavor',
               default=3,
               help='id of machine flavor used for nodes (3=medium)'),
    cfg.IntOpt('gateway_flavor',
               default=1,
               help='id of machine flavor used to construct GW (1=tiny)'),
    cfg.StrOpt('key_name',
               default='shared',
               help='name of public key for node access via ssh'),
    cfg.ListOpt('security_groups',
                default=['default', 'ssh'],
                help='list of security groups (firewall rules) for nodes'),
    cfg.StrOpt('src_dir',
               default='../bin/',
               help='relative source location (to __file__) of various'
                    ' chef-related setup scripts on client'),
    cfg.StrOpt('dst_dir',
               default='/home/ubuntu/',
               help='absolute destination path for chef-related setup scripts'
                    ' on nodes'),
    cfg.StrOpt('userdata',
               default='userdata.sh.template',
               help='bash script run by cloud-init in late boot stage'
                    ' (rc.local-like)'),
    cfg.IntOpt('timeout',
               default=999999,
               help='maximum time (in seconds) to wait for all nodes to be'
                    ' ready [ssh-able + userdata]'),
    cfg.IntOpt('poll_interval',
               default=5,
               help='interval (in seconds) between readiness polls'),
]

cmd_opts = [
    cfg.BoolOpt('shell',
                default=False,
                help='initialize, then drop to embedded IPython shell'),
    cfg.BoolOpt('cleanup',
                default=False,
                help='take down the inception cloud'),
]

CONF = cfg.CONF
CONF.register_cli_opts(orchestrator_opts)
CONF.register_cli_opts(cmd_opts)


class Orchestrator(object):
    """
    orchestrate all inception cloud stuff
    """

    def __init__(self,
                 prefix,
                 num_workers,
                 atomic,
                 parallel,
                 chef_repo,
                 chef_repo_branch,
                 ssh_keyfile,
                 pool,
                 user,
                 image,
                 flavor,
                 gateway_flavor,
                 key_name,
                 security_groups,
                 src_dir,
                 dst_dir,
                 userdata,
                 timeout,
                 poll_interval):
        """
        For doc on each param refer to orchestrator_opts
        """
        ## check args
        #TODO(changbl): remove the restriction of "num_workers <= 5"
        if num_workers > 5:
            raise ValueError("currently only supports num_workers <= 5")
        #TODO(changbl): make separator '-' a constant and accessible
        #everywhere
        if '-' in prefix:
            raise ValueError('"-" cannot exist in prefix=%r' % prefix)
        ## args
        self.prefix = prefix
        self.num_workers = num_workers
        self.atomic = atomic
        self.parallel = parallel
        self.chef_repo = chef_repo
        self.chef_repo_branch = chef_repo_branch
        self.ssh_keyfile = ssh_keyfile
        self.pool = pool
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
        # Inject the extra ssh public key if any
        ssh_keycontent = ''
        if self.ssh_keyfile:
            with open(self.ssh_keyfile, 'r') as fin:
                ssh_keycontent = fin.read()
        self.userdata = self.userdata % (user, ssh_keycontent)
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

    def start(self):
        """
        run the whole process
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
            if self.atomic:
                self.cleanup()

    def _check_existence(self):
        """
        Check whether inception cloud existence based on given self.prefix
        """
        full_prefix = self.prefix + '-'
        for server in self.client.servers.list():
            if server.name.startswith(full_prefix):
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

        print ('wait at most %s seconds for servers to be ready (ssh-able + '
               'userdata done)' % self.timeout)
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
                # clear content upon each time retry
                self._worker_ips = []
                self._worker_names = []
                for _id in self._worker_ids:
                    (ipaddr, name) = self._get_server_info(_id)
                    self._worker_ips.append(ipaddr)
                    self._worker_names.append(name)
                # test ssh-able
                command = '[ -d /etc/inception ]'
                cmd.ssh(self.user + "@" + self._gateway_ip, command)
                cmd.ssh(self.user + "@" + self._chefserver_ip, command)
                cmd.ssh(self.user + "@" + self._controller_ip, command)
                for worker_ip in self._worker_ips:
                    cmd.ssh(self.user + "@" + worker_ip, command)
                # indicate that servers are ready
                servers_ready = True
                break
            except (UnboundLocalError, subprocess.CalledProcessError) as error:
                print ('servers are not all ready, error=%s, sleep %s seconds'
                       % (error, self.poll_interval))
                time.sleep(self.poll_interval)
                continue
        if not servers_ready:
            raise RuntimeError("No all servers can be brought up")

        # create a public IP and associate it to gateway
        floating_ip = self.client.floating_ips.create(pool=self.pool)
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
        funcs = []
        ipaddrs = ([self._chefserver_ip, self._gateway_ip,
                    self._controller_ip] + self._worker_ips)
        hostnames = ([self._chefserver_name, self._gateway_name,
                      self._controller_name] + self._worker_names)
        for (ipaddr, hostname) in zip(ipaddrs, hostnames):
            uri = self.user + '@' + self._chefserver_ip
            command = ('/usr/bin/knife bootstrap %s -x %s -N %s -E %s --sudo'
                       % (ipaddr, self.user, hostname, self.prefix))
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)
        # run an empty list to make sure attributes are properly propagated
        self._run_chef_client(ipaddrs)
        # sleep some time
        time.sleep(5)

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
        funcs = []
        for hostname in hostnames:
            uri = self.user + '@' + self._chefserver_ip
            command = "/usr/bin/knife node run_list add %s %s" % (
                hostname, item)
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)

    def _run_chef_client(self, ipaddrs):
        """
        for each server in the address list, run chef-client for all
        specified cookbooks in its run_list

        @param param: ip addresses of the servers
        """
        funcs = []
        for ipaddr in ipaddrs:
            uri = self.user + '@' + ipaddr
            command = "sudo chef-client"
            func = functools.partial(cmd.ssh, uri, command, screen_output=True,
                                     agent_forwarding=True)
            funcs.append(func)
        self._execute_funcs(funcs)

    def _execute_funcs(self, funcs):
        """
        Execute functions, whether in parallel (via threads) or
            sequential.  If parallel, exceptions of subthreads will be
            collected in a shared queue, and an exception will raised
            in main thread later

        @param funcs: the functions to be executed
        """
        if not self.parallel:
            for func in funcs:
                func()
        else:
            exception_queue = Queue.Queue()
            threads = []
            # create and start all threads
            for func in funcs:
                thread = wrapper.FuncThread(func, exception_queue)
                threads.append(thread)
                thread.start()
            # wait for all threads to finish
            for thread in threads:
                thread.join()
            # check whether got exception in threads
            got_exception = not exception_queue.empty()
            while not exception_queue.empty():
                thread_name, func_info, exc = exception_queue.get()
                print thread_name, func_info, exc
            if got_exception:
                raise RuntimeError("One or more subthreads got exception")

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
    # processes args
    try:
        CONF(args=sys.argv[1:], version="Inception: version %s" % __version__)
    except Exception as e:
        print e
        sys.exit(1)
    # start orchestator
    orchestrator = Orchestrator(CONF.prefix,
                                CONF.num_workers,
                                CONF.atomic,
                                CONF.parallel,
                                CONF.chef_repo,
                                CONF.chef_repo_branch,
                                CONF.ssh_keyfile,
                                CONF.pool,
                                CONF.user,
                                CONF.image,
                                CONF.flavor,
                                CONF.gateway_flavor,
                                CONF.key_name,
                                CONF.security_groups,
                                CONF.src_dir,
                                CONF.dst_dir,
                                CONF.userdata,
                                CONF.timeout,
                                CONF.poll_interval)
    if CONF.shell:
        # give me a ipython shell
        IPython.embed()
        return
    if CONF.cleanup:
        orchestrator.cleanup()
    else:
        orchestrator.start()

##############################################
if __name__ == "__main__":
    main()
